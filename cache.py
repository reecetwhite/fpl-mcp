import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TypedDict, cast

import httpx

FPL_BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"


class Element(TypedDict):
    id: int
    web_name: str
    first_name: str
    second_name: str
    team: int
    element_type: int
    now_cost: int
    total_points: int
    form: str
    selected_by_percent: str


class Team(TypedDict):
    id: int
    name: str
    short_name: str
    strength: int
    strength_overall_home: int
    strength_overall_away: int
    strength_attack_home: int
    strength_attack_away: int
    strength_defence_home: int
    strength_defence_away: int


class Event(TypedDict):
    id: int
    name: str
    finished: bool


class BootstrapData(TypedDict):
    elements: list[Element]
    teams: list[Team]
    events: list[Event]


@dataclass
class FPLCache:
    ttl_seconds: int = 300

    _data: BootstrapData | None = field(default=None)
    _last_fetch: datetime | None = field(default=None)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    # Indexes
    _elements_by_id: dict[int, Element] = field(default_factory=dict)
    _elements_by_name: dict[str, list[Element]] = field(default_factory=dict)
    _elements_by_team: dict[int, list[Element]] = field(default_factory=dict)
    _teams_by_id: dict[int, Team] = field(default_factory=dict)
    _teams_by_name: dict[str, Team] = field(default_factory=dict)
    _events_by_id: dict[int, Event] = field(default_factory=dict)

    def _is_stale(self) -> bool:
        if self._last_fetch is None:
            return True
        return datetime.now() - self._last_fetch > timedelta(seconds=self.ttl_seconds)

    def _build_indexes(self) -> None:
        self._elements_by_id.clear()
        self._elements_by_name.clear()
        self._elements_by_team.clear()
        self._teams_by_id.clear()
        self._teams_by_name.clear()
        self._events_by_id.clear()

        if self._data is None:
            return

        for el in self._data["elements"]:
            self._elements_by_id[el["id"]] = el

            # Index by web_name (display name) lowercase
            name_key = el["web_name"].lower()
            self._elements_by_name.setdefault(name_key, []).append(el)

            # Also index by full name
            full_name = f"{el['first_name']} {el['second_name']}".lower()
            if full_name != name_key:
                self._elements_by_name.setdefault(full_name, []).append(el)

            # Index by team
            self._elements_by_team.setdefault(el["team"], []).append(el)

        for team in self._data["teams"]:
            self._teams_by_id[team["id"]] = team
            self._teams_by_name[team["name"].lower()] = team
            self._teams_by_name[team["short_name"].lower()] = team

        for event in self._data["events"]:
            self._events_by_id[event["id"]] = event

    async def _fetch(self) -> BootstrapData:
        async with httpx.AsyncClient() as client:
            resp = await client.get(FPL_BOOTSTRAP_URL, timeout=30)
            _ = resp.raise_for_status()
            return cast(BootstrapData, resp.json())

    async def refresh(self, force: bool = False) -> None:
        async with self._lock:
            if not force and not self._is_stale():
                return

            try:
                self._data = await self._fetch()
                self._last_fetch = datetime.now()
                self._build_indexes()
            except Exception:
                # If we have stale data, keep using it
                if self._data:
                    return
                raise

    async def ensure_loaded(self) -> None:
        if self._is_stale():
            await self.refresh()

    def get_element(self, player_id: int) -> Element | None:
        return self._elements_by_id.get(player_id)

    def search_elements(self, query: str) -> list[Element]:
        query = query.lower()
        results: list[Element] = []

        # Exact match first
        if query in self._elements_by_name:
            results.extend(self._elements_by_name[query])

        # Partial match
        for name, players in self._elements_by_name.items():
            if query in name and name != query:
                for p in players:
                    if p not in results:
                        results.append(p)

        return results

    def get_team(self, team_id: int) -> Team | None:
        return self._teams_by_id.get(team_id)

    def get_team_name(self, team_id: int) -> str:
        team = self._teams_by_id.get(team_id)
        return team["short_name"] if team else "Unknown"

    def search_teams(self, query: str) -> list[Team]:
        query = query.lower()
        results: list[Team] = []
        for name, team in self._teams_by_name.items():
            if query in name and team not in results:
                results.append(team)
        return results

    def get_all_teams(self) -> list[Team]:
        return list(self._teams_by_id.values())

    def get_position_name(self, element_type: int) -> str:
        positions = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
        return positions.get(element_type, "???")

    def stats(self) -> tuple[int, int]:
        """Return (player_count, team_count)."""
        return len(self._elements_by_id), len(self._teams_by_id)

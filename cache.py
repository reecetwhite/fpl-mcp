import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TypedDict, cast

import httpx

FPL_BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
FPL_FIXTURES_URL = "https://fantasy.premierleague.com/api/fixtures/"


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
    # Core performance
    minutes: int
    starts: int
    goals_scored: int
    assists: int
    bonus: int
    yellow_cards: int
    red_cards: int
    # Defensive
    clean_sheets: int
    goals_conceded: int
    saves: int
    # xG stats
    expected_goals: str
    expected_assists: str
    # Availability
    status: str
    chance_of_playing_next_round: int | None
    news: str
    # Efficiency
    points_per_game: str
    defensive_contribution_per_90: str


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
    is_current: bool
    is_next: bool
    deadline_time: str


class Fixture(TypedDict):
    id: int
    event: int | None
    kickoff_time: str | None
    team_h: int
    team_a: int
    team_h_score: int | None
    team_a_score: int | None
    finished: bool
    team_h_difficulty: int
    team_a_difficulty: int


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

    # Fixtures
    _fixtures: list[Fixture] = field(default_factory=list)
    _fixtures_last_fetch: datetime | None = field(default=None)
    _fixtures_by_id: dict[int, Fixture] = field(default_factory=dict)
    _fixtures_by_event: dict[int, list[Fixture]] = field(default_factory=dict)
    _fixtures_by_team: dict[int, list[Fixture]] = field(default_factory=dict)

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
        if self._is_fixtures_stale():
            await self.refresh_fixtures()

    def _is_fixtures_stale(self) -> bool:
        if self._fixtures_last_fetch is None:
            return True
        return datetime.now() - self._fixtures_last_fetch > timedelta(seconds=self.ttl_seconds)

    async def _fetch_fixtures(self) -> list[Fixture]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(FPL_FIXTURES_URL, timeout=30)
            _ = resp.raise_for_status()
            return cast(list[Fixture], resp.json())

    def _build_fixture_indexes(self) -> None:
        self._fixtures_by_id.clear()
        self._fixtures_by_event.clear()
        self._fixtures_by_team.clear()

        for fix in self._fixtures:
            self._fixtures_by_id[fix["id"]] = fix

            event = fix.get("event")
            if event is not None:
                self._fixtures_by_event.setdefault(event, []).append(fix)

            self._fixtures_by_team.setdefault(fix["team_h"], []).append(fix)
            self._fixtures_by_team.setdefault(fix["team_a"], []).append(fix)

    async def refresh_fixtures(self, force: bool = False) -> None:
        async with self._lock:
            if not force and not self._is_fixtures_stale():
                return

            try:
                self._fixtures = await self._fetch_fixtures()
                self._fixtures_last_fetch = datetime.now()
                self._build_fixture_indexes()
            except Exception:
                if self._fixtures:
                    return
                raise

    # ── Elements ─────────────────────────────────────────────────────────

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

    # ── Teams ────────────────────────────────────────────────────────────

    def get_team(self, team_id: int) -> Team | None:
        return self._teams_by_id.get(team_id)

    def search_teams(self, query: str) -> list[Team]:
        query = query.lower()
        results: list[Team] = []
        for name, team in self._teams_by_name.items():
            if query in name and team not in results:
                results.append(team)
        return results

    def get_all_teams(self) -> list[Team]:
        return list(self._teams_by_id.values())

    # ── Events ──────────────────────────────────────────────────────────

    def get_current_gameweek(self) -> int | None:
        for event in self._events_by_id.values():
            if event.get("is_current"):
                return event["id"]
        # Fallback to next if no current
        for event in self._events_by_id.values():
            if event.get("is_next"):
                return event["id"]
        return None

    def get_event(self, event_id: int) -> Event | None:
        return self._events_by_id.get(event_id)

    # ── Fixtures ────────────────────────────────────────────────────────

    def get_fixtures_by_event(self, event_id: int) -> list[Fixture]:
        return self._fixtures_by_event.get(event_id, [])

    def get_fixtures_by_team(self, team_id: int) -> list[Fixture]:
        return self._fixtures_by_team.get(team_id, [])

    # ── Utilities ────────────────────────────────────────────────────────

    def get_position_name(self, element_type: int) -> str:
        positions = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
        return positions.get(element_type, "???")

    def stats(self) -> tuple[int, int, int]:
        """Return (player_count, team_count, fixture_count)."""
        return len(self._elements_by_id), len(self._teams_by_id), len(self._fixtures)

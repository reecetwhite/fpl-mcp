from collections.abc import Callable

from fastmcp import FastMCP

from cache import Element, Fixture, FPLCache, Team

mcp = FastMCP("fpl-mcp")
cache = FPLCache()


def format_player(p: Element) -> str:
    team = cache.get_team(p["team"])
    team_name = team["short_name"] if team else "Unknown"
    pos = cache.get_position_name(p["element_type"])
    price = p["now_cost"] / 10
    element_type = p["element_type"]

    # Base stats for all positions
    parts = [
        f"{p['web_name']} ({team_name} {pos}) £{price}m",
        f"{p['total_points']}pts ({p['points_per_game']}/g)",
        f"form:{p['form']}",
        f"{p['selected_by_percent']}%",
        f"{p['minutes']}min",
        f"{p['goals_scored']}g {p['assists']}a {p['bonus']}bps",
    ]

    # Position-specific stats
    if element_type == 1:  # GKP
        parts.append(f"{p['saves']}sv {p['clean_sheets']}cs")
    elif element_type == 2:  # DEF
        parts.append(f"{p['clean_sheets']}cs {p['goals_conceded']}gc | xG:{p['expected_goals']} xA:{p['expected_assists']} | def/90:{p['defensive_contribution_per_90']}")
    elif element_type == 3:  # MID
        parts.append(f"xG:{p['expected_goals']} xA:{p['expected_assists']} | {p['clean_sheets']}cs | def/90:{p['defensive_contribution_per_90']}")
    else:  # FWD
        parts.append(f"xG:{p['expected_goals']} xA:{p['expected_assists']}")

    # Cards if any
    if p["yellow_cards"] or p["red_cards"]:
        parts.append(f"{p['yellow_cards']}Y {p['red_cards']}R")

    # Availability flag if not available
    if p["status"] != "a":
        status_map = {"d": "doubtful", "i": "injured", "n": "unavailable", "s": "suspended", "u": "unavailable"}
        status_text = status_map.get(p["status"], p["status"])
        chance = p.get("chance_of_playing_next_round")
        chance_str = f" {chance}%" if chance is not None else ""
        news = p.get("news", "")
        news_str = f" - {news}" if news else ""
        parts.append(f"⚠️ {status_text}{chance_str}{news_str}")

    return " | ".join(parts)


def format_team(t: Team) -> str:
    return (
        f"{t['name']} ({t['short_name']}) | strength: {t['strength']} | "
        f"home: {t['strength_overall_home']} atk:{t['strength_attack_home']} def:{t['strength_defence_home']} | "
        f"away: {t['strength_overall_away']} atk:{t['strength_attack_away']} def:{t['strength_defence_away']}"
    )


def format_fixture(fix: Fixture, team_perspective: int | None = None) -> str:
    """Format fixture. If team_perspective given, show opponent with H/A and FDR."""
    home = cache.get_team(fix["team_h"])
    away = cache.get_team(fix["team_a"])
    home_name = home["short_name"] if home else "???"
    away_name = away["short_name"] if away else "???"

    event = fix.get("event")
    gw = f"GW{event}" if event else "TBD"

    kickoff = fix.get("kickoff_time")
    if kickoff:
        # Parse ISO format and format nicely
        dt = kickoff.replace("T", " ")[:16]  # "2024-01-25 15:00"
    else:
        dt = "TBD"

    if fix["finished"] and fix["team_h_score"] is not None:
        score = f"{fix['team_h_score']}-{fix['team_a_score']}"
    else:
        score = None

    if team_perspective:
        if team_perspective == fix["team_h"]:
            opp = away_name
            venue = "H"
            fdr = fix["team_h_difficulty"]
        else:
            opp = home_name
            venue = "A"
            fdr = fix["team_a_difficulty"]

        if score:
            return f"{gw}: {opp} ({venue}) FDR:{fdr} | {score} | {dt}"
        return f"{gw}: {opp} ({venue}) FDR:{fdr} | {dt}"

    # Neutral format
    if score:
        return f"{gw}: {home_name} {score} {away_name} | {dt}"
    return f"{gw}: {home_name} vs {away_name} | {dt}"


# ── Helper Functions ─────────────────────────────────────────────────────


def resolve_position(position: str | None) -> int | None:
    if not position:
        return None
    pos_map = {"gkp": 1, "gk": 1, "def": 2, "mid": 3, "fwd": 4, "forward": 4}
    return pos_map.get(position.lower())


def resolve_team_id(team: str | None) -> int | None:
    if not team:
        return None
    results = cache.search_teams(team)
    return results[0]["id"] if results else None


# ── Player Tools ─────────────────────────────────────────────────────────


@mcp.tool()
async def get_player(player_id: int) -> str:
    """Get FPL player info by ID."""
    await cache.ensure_loaded()
    player = cache.get_element(player_id)
    if not player:
        return f"Player {player_id} not found"
    return format_player(player)


@mcp.tool()
async def search_player(name: str) -> str:
    """Search FPL players by name (partial match)."""
    await cache.ensure_loaded()
    results = cache.search_elements(name)
    if not results:
        return f"No players found matching '{name}'"
    if len(results) > 10:
        lines = [f"Found {len(results)} players, showing top 10:"]
    else:
        lines = [f"Found {len(results)} player(s):"]
    for p in results[:10]:
        lines.append(format_player(p))
    return "\n".join(lines)


# ── Analysis Tools ───────────────────────────────────────────────────────


@mcp.tool()
async def filter_players(
    position: str | None = None,
    team: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_form: float | None = None,
    min_points: int | None = None,
    available_only: bool = False,
    sort_by: str = "total_points",
    limit: int = 20,
) -> str:
    """Filter players by position, team, price, form, points, availability."""
    await cache.ensure_loaded()

    pos_id = resolve_position(position)
    team_id = resolve_team_id(team)

    players = cache.get_all_elements()

    # Apply filters
    if pos_id:
        players = [p for p in players if p["element_type"] == pos_id]
    if team_id:
        players = [p for p in players if p["team"] == team_id]
    if min_price is not None:
        players = [p for p in players if p["now_cost"] / 10 >= min_price]
    if max_price is not None:
        players = [p for p in players if p["now_cost"] / 10 <= max_price]
    if min_form is not None:
        players = [p for p in players if float(p["form"]) >= min_form]
    if min_points is not None:
        players = [p for p in players if p["total_points"] >= min_points]
    if available_only:
        players = [p for p in players if p["status"] == "a"]

    if not players:
        return "No players match the filters"

    # Sort
    sort_key_map: dict[str, Callable[[Element], float]] = {
        "total_points": lambda p: p["total_points"],
        "points": lambda p: p["total_points"],
        "form": lambda p: float(p["form"]),
        "price": lambda p: p["now_cost"],
        "points_per_game": lambda p: float(p["points_per_game"]),
        "ppg": lambda p: float(p["points_per_game"]),
        "ownership": lambda p: float(p["selected_by_percent"]),
    }
    sort_fn = sort_key_map.get(sort_by.lower(), lambda p: p["total_points"])
    reverse = sort_by.lower() != "price"
    players_sorted = sorted(players, key=sort_fn, reverse=reverse)[:limit]

    lines = [f"Found {len(players)} players (showing {len(players_sorted)}):"]
    for p in players_sorted:
        lines.append(format_player(p))
    return "\n".join(lines)


@mcp.tool()
async def get_top_players(
    metric: str,
    position: str | None = None,
    limit: int = 10,
) -> str:
    """Get top players by metric: points, form, points_per_game, x_g, x_a, value."""
    await cache.ensure_loaded()

    pos_id = resolve_position(position)
    players = cache.get_all_elements()

    if pos_id:
        players = [p for p in players if p["element_type"] == pos_id]

    metric_lower = metric.lower()
    metric_map: dict[str, tuple[str, Callable[[Element], float]]] = {
        "points": ("total_points", lambda p: p["total_points"]),
        "total_points": ("total_points", lambda p: p["total_points"]),
        "form": ("form", lambda p: float(p["form"])),
        "points_per_game": ("ppg", lambda p: float(p["points_per_game"])),
        "ppg": ("ppg", lambda p: float(p["points_per_game"])),
        "x_g": ("xG", lambda p: float(p["expected_goals"])),
        "x_a": ("xA", lambda p: float(p["expected_assists"])),
        "value": ("value", lambda p: p["total_points"] / (p["now_cost"] / 10) if p["minutes"] > 0 else 0),
    }

    if metric_lower not in metric_map:
        return f"Unknown metric '{metric}'. Valid: points, form, points_per_game, x_g, x_a, value"

    label, key_fn = metric_map[metric_lower]

    # For value, filter out 0-minute players
    if metric_lower == "value":
        players = [p for p in players if p["minutes"] > 0]

    players_sorted = sorted(players, key=key_fn, reverse=True)[:limit]

    pos_label = f" {position.upper()}" if position else ""
    lines = [f"Top {limit}{pos_label} by {label}:"]
    for i, p in enumerate(players_sorted, 1):
        val = key_fn(p)
        if isinstance(val, float):
            val = f"{val:.2f}"
        lines.append(f"{i}. {format_player(p)} [{label}={val}]")
    return "\n".join(lines)


@mcp.tool()
async def get_differentials(
    max_ownership: float = 10.0,
    min_form: float = 5.0,
    position: str | None = None,
    limit: int = 10,
) -> str:
    """Find differential picks: low ownership, high form, available."""
    await cache.ensure_loaded()

    pos_id = resolve_position(position)
    players = cache.get_all_elements()

    # Filter
    if pos_id:
        players = [p for p in players if p["element_type"] == pos_id]

    players = [
        p for p in players
        if float(p["selected_by_percent"]) <= max_ownership
        and float(p["form"]) >= min_form
        and p["status"] == "a"
    ]

    if not players:
        return f"No differentials found (ownership ≤{max_ownership}%, form ≥{min_form})"

    players_sorted = sorted(players, key=lambda p: float(p["form"]), reverse=True)[:limit]

    pos_label = f" {position.upper()}" if position else ""
    lines = [f"Differentials{pos_label} (≤{max_ownership}% owned, ≥{min_form} form):"]
    for p in players_sorted:
        lines.append(format_player(p))
    return "\n".join(lines)


@mcp.tool()
async def compare_players(player_names: list[str]) -> str:
    """Compare multiple players side-by-side."""
    await cache.ensure_loaded()

    if len(player_names) > 10:
        return "Maximum 10 players for comparison"

    players: list[Element] = []
    not_found: list[str] = []

    for name in player_names:
        results = cache.search_elements(name)
        if results:
            players.append(results[0])
        else:
            not_found.append(name)

    if not players:
        return f"No players found: {', '.join(not_found)}"

    lines = ["Player Comparison:"]
    lines.append("-" * 60)

    for p in players:
        team = cache.get_team(p["team"])
        team_name = team["short_name"] if team else "???"
        pos = cache.get_position_name(p["element_type"])
        price = p["now_cost"] / 10

        lines.append(f"\n**{p['web_name']}** ({team_name} {pos}) £{price}m")
        lines.append(f"  Points: {p['total_points']} | Form: {p['form']} | PPG: {p['points_per_game']}")
        lines.append(f"  xG: {p['expected_goals']} | xA: {p['expected_assists']}")
        lines.append(f"  Ownership: {p['selected_by_percent']}%")
        if p["status"] != "a":
            lines.append(f"  ⚠️ Status: {p['status']} - {p.get('news', '')}")

    if not_found:
        lines.append(f"\nNot found: {', '.join(not_found)}")

    return "\n".join(lines)


# ── Team Tools ───────────────────────────────────────────────────────────


@mcp.tool()
async def get_team(team_id: int) -> str:
    """Get FPL team info by ID."""
    await cache.ensure_loaded()
    team = cache.get_team(team_id)
    if not team:
        return f"Team {team_id} not found"
    return format_team(team)


@mcp.tool()
async def search_team(name: str) -> str:
    """Search FPL teams by name (partial match)."""
    await cache.ensure_loaded()
    results = cache.search_teams(name)
    if not results:
        return f"No teams found matching '{name}'"
    lines = [f"Found {len(results)} team(s):"]
    for t in results:
        lines.append(format_team(t))
    return "\n".join(lines)


@mcp.tool()
async def get_all_teams() -> str:
    """Get all Premier League teams sorted by strength."""
    await cache.ensure_loaded()
    teams = cache.get_all_teams()
    teams_sorted = sorted(teams, key=lambda t: t["strength"], reverse=True)
    lines = ["All 20 Premier League teams (sorted by strength):"]
    for t in teams_sorted:
        lines.append(format_team(t))
    return "\n".join(lines)


# ── Fixture Tools ────────────────────────────────────────────────────────


@mcp.tool()
async def get_gameweek_fixtures(gameweek: int) -> str:
    """Get all fixtures for a specific gameweek."""
    await cache.ensure_loaded()

    fixtures = cache.get_fixtures_by_event(gameweek)
    if not fixtures:
        return f"No fixtures found for GW{gameweek}"

    # Sort by kickoff time
    fixtures_sorted = sorted(fixtures, key=lambda f: f.get("kickoff_time") or "")
    lines = [f"GW{gameweek} fixtures ({len(fixtures)} matches):"]
    for fix in fixtures_sorted:
        lines.append(format_fixture(fix))
    return "\n".join(lines)


@mcp.tool()
async def get_team_fixtures(team: str, gameweek: int | None = None) -> str:
    """Get fixtures for a team, optionally filtered by gameweek."""
    await cache.ensure_loaded()

    teams = cache.search_teams(team)
    if not teams:
        return f"Team '{team}' not found"
    t = teams[0]

    fixtures = cache.get_fixtures_by_team(t["id"])
    if gameweek:
        fixtures = [f for f in fixtures if f.get("event") == gameweek]

    if not fixtures:
        return f"No fixtures found for {t['name']}"

    # Sort by event then kickoff
    fixtures_sorted = sorted(fixtures, key=lambda f: (f.get("event") or 99, f.get("kickoff_time") or ""))
    gw_filter = f" (GW{gameweek})" if gameweek else ""
    lines = [f"{t['name']} fixtures{gw_filter}:"]
    for fix in fixtures_sorted:
        lines.append(format_fixture(fix, team_perspective=t["id"]))
    return "\n".join(lines)


@mcp.tool()
async def get_team_upcoming(team: str, limit: int = 5) -> str:
    """Get next N upcoming fixtures for a team with FDR ratings."""
    await cache.ensure_loaded()

    teams = cache.search_teams(team)
    if not teams:
        return f"Team '{team}' not found"
    t = teams[0]

    current_gw = cache.get_current_gameweek()
    if not current_gw:
        return "Could not determine current gameweek"

    fixtures = cache.get_fixtures_by_team(t["id"])
    # Filter to current GW onwards and not finished
    upcoming = [f for f in fixtures if (ev := f.get("event")) is not None and ev >= current_gw and not f["finished"]]
    upcoming_sorted = sorted(upcoming, key=lambda f: (f.get("event") or 99, f.get("kickoff_time") or ""))[:limit]

    if not upcoming_sorted:
        return f"No upcoming fixtures found for {t['name']}"

    lines = [f"{t['name']} next {len(upcoming_sorted)} fixtures:"]
    for fix in upcoming_sorted:
        lines.append(format_fixture(fix, team_perspective=t["id"]))
    return "\n".join(lines)


@mcp.tool()
async def get_next_gameweeks(count: int = 5) -> str:
    """Get summary of upcoming gameweeks with all fixtures."""
    await cache.ensure_loaded()

    current_gw = cache.get_current_gameweek()
    if not current_gw:
        return "Could not determine current gameweek"

    lines: list[str] = []
    for gw in range(current_gw, current_gw + count):
        event = cache.get_event(gw)
        if not event:
            continue

        fixtures = cache.get_fixtures_by_event(gw)
        fixtures_sorted = sorted(fixtures, key=lambda f: f.get("kickoff_time") or "")

        deadline = event.get("deadline_time", "")
        if deadline:
            deadline = deadline.replace("T", " ")[:16]

        lines.append(f"\n## GW{gw} (deadline: {deadline})")
        for fix in fixtures_sorted:
            lines.append(format_fixture(fix))

    if not lines:
        return "No upcoming gameweeks found"

    return "\n".join(lines)


# ── Utility ──────────────────────────────────────────────────────────────


@mcp.tool()
async def refresh_cache() -> str:
    """Force refresh the FPL data cache."""
    await cache.refresh(force=True)
    await cache.refresh_fixtures(force=True)
    players, teams, fixtures = cache.stats()
    return f"Cache refreshed: {players} players, {teams} teams, {fixtures} fixtures"


def main():
    mcp.run()


if __name__ == "__main__":
    main()

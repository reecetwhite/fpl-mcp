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

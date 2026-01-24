from fastmcp import FastMCP

from cache import Element, FPLCache, Team

mcp = FastMCP("fpl-mcp")
cache = FPLCache()


def format_player(p: Element) -> str:
    team = cache.get_team(p["team"])
    team_name = team["short_name"] if team else "Unknown"
    pos = cache.get_position_name(p["element_type"])
    price = p["now_cost"] / 10
    pts = p["total_points"]
    form = p["form"]
    selected = p["selected_by_percent"]
    return f"{p['web_name']} ({team_name} {pos}) £{price}m | {pts}pts | form:{form} | {selected}%"


def format_team(t: Team) -> str:
    return (
        f"{t['name']} ({t['short_name']}) | strength: {t['strength']} | "
        f"home: {t['strength_overall_home']} atk:{t['strength_attack_home']} def:{t['strength_defence_home']} | "
        f"away: {t['strength_overall_away']} atk:{t['strength_attack_away']} def:{t['strength_defence_away']}"
    )


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


# ── Utility ──────────────────────────────────────────────────────────────


@mcp.tool()
async def refresh_cache() -> str:
    """Force refresh the FPL data cache."""
    await cache.refresh(force=True)
    players, teams = cache.stats()
    return f"Cache refreshed: {players} players, {teams} teams"


def main():
    mcp.run()


if __name__ == "__main__":
    main()

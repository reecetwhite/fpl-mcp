from mcp.server.fastmcp import FastMCP

from cache import Element, FPLCache

mcp = FastMCP("fpl-mcp")
cache = FPLCache()


def format_player(p: Element) -> str:
    team = cache.get_team_name(p["team"])
    pos = cache.get_position_name(p["element_type"])
    price = p["now_cost"] / 10
    pts = p["total_points"]
    form = p["form"]
    selected = p["selected_by_percent"]
    return f"{p['web_name']} ({team} {pos}) £{price}m | {pts}pts | form:{form} | {selected}%"


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

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("fpl-mcp")


@mcp.tool()
async def get_player(player_id: int) -> str:
    """Get FPL player info by ID."""
    # TODO: implement FPL API call
    return f"Player {player_id}"


def main():
    mcp.run()

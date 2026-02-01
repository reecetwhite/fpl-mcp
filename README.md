<div align="center">
  <h1><code>fpl-mcp</code></h1>
  <p>MCP server for the Fantasy Premier League API.</p>
  <p><i>Query players, teams, fixtures, and your FPL team through any MCP-compatible client.</i></p>
</div>

## Features

- **Player Data** — Search, filter, and compare players by stats, price, form, ownership
- **Team Analysis** — View Premier League team info and strength ratings
- **Fixtures** — Browse gameweek fixtures, team schedules, and FDR ratings
- **Your Team** — Fetch your FPL squad (via manager ID or API token)
- **Differentials** — Find low-ownership, high-form picks
- **Auto-caching** — Data cached locally with manual refresh option

## Prerequisites

- Python 3.11+
- [just](https://github.com/casey/just) (command runner)

## Installation

```bash
git clone https://github.com/yourusername/fpl-mcp.git
cd fpl-mcp

just create-venv
just install
```

### Configuration (optional)

Copy `.env.example` to `.env` to configure your manager ID:

```bash
cp .env.example .env
```

```env
# Your FPL manager ID (from URL: fantasy.premierleague.com/entry/XXXXXX/...)
FPL_MANAGER_ID=123456

# Optional: API token for authenticated requests
FPL_API_TOKEN=
```

## Client Setup

### Claude Code

Add to `~/.claude/mcp_servers.json`:

```json
{
  "fpl-mcp": {
    "command": "/path/to/fpl-mcp/.venv/bin/python",
    "args": ["-m", "src.server"],
    "cwd": "/path/to/fpl-mcp",
    "env": {
      "FPL_MANAGER_ID": "123456"
    }
  }
}
```

### Claude Desktop

Add to Claude Desktop config:

```json
{
  "mcpServers": {
    "fpl-mcp": {
      "command": "/path/to/fpl-mcp/.venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/fpl-mcp",
      "env": {
        "FPL_MANAGER_ID": "123456"
      }
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json` in your project or `~/.cursor/mcp.json` globally:

```json
{
  "mcpServers": {
    "fpl-mcp": {
      "command": "/path/to/fpl-mcp/.venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/fpl-mcp",
      "env": {
        "FPL_MANAGER_ID": "123456"
      }
    }
  }
}
```

## Usage

| Command | Description |
|---------|-------------|
| `just info` | Show project info |
| `just run` | Run the MCP server |
| `just test` | Run tests |
| `just lint` | Lint with ruff |
| `just fmt` | Format with ruff |

## Tools

### Player Tools

| Tool | Description |
|------|-------------|
| `get_player` | Get player info by ID |
| `search_player` | Search players by name (partial match) |
| `filter_players` | Filter by position, team, price, form, points, availability |
| `get_top_players` | Rank by metric: points, form, ppg, xG, xA, value |
| `get_differentials` | Find low-ownership picks with high form |
| `compare_players` | Side-by-side comparison of multiple players |

### Team Tools

| Tool | Description |
|------|-------------|
| `get_team` | Get team info by ID |
| `search_team` | Search teams by name |
| `get_all_teams` | List all 20 PL teams sorted by strength |

### Fixture Tools

| Tool | Description |
|------|-------------|
| `get_gameweek_fixtures` | All fixtures for a gameweek |
| `get_team_fixtures` | Team's fixtures (optionally by gameweek) |
| `get_team_upcoming` | Next N fixtures with FDR ratings |
| `get_next_gameweeks` | Overview of upcoming gameweeks |

### Manager Tools

| Tool | Description |
|------|-------------|
| `get_my_team` | Fetch your current FPL squad |

### Utility

| Tool | Description |
|------|-------------|
| `refresh_cache` | Force refresh cached FPL data |

## License

MIT

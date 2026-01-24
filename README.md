# FPL MCP Server

MCP server for Fantasy Premier League API.

## Install

```bash
pip install -e .
```

## Run

```bash
python server.py
# or after install:
fpl-mcp
```

## Claude Desktop Config

```json
{
  "mcpServers": {
    "fpl": {
      "command": "python",
      "args": ["server.py"]
    }
  }
}
```

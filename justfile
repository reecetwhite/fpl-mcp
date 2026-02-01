# Show project info
info:
    @echo "fpl-mcp: MCP server for the Fantasy Premier League API"
    @echo ""
    @echo "Python: $(.venv/bin/python --version 2>/dev/null || echo 'venv not created')"
    @echo "FastMCP: $(.venv/bin/pip show fastmcp 2>/dev/null | grep Version | cut -d' ' -f2 || echo 'not installed')"

# Check helpers
[private]
check-venv:
    @test -f .venv/bin/python || (echo "Error: venv not found. Run: just create-venv" && exit 1)

[private]
check-deps: check-venv
    @.venv/bin/pip show fastmcp >/dev/null 2>&1 || (echo "Error: deps missing. Run: just install" && exit 1)

[private]
check-dev-deps: check-venv
    @.venv/bin/pip show ruff >/dev/null 2>&1 || (echo "Error: dev deps missing. Run: just install-dev" && exit 1)

# Create venv
create-venv:
    python -m venv .venv

# Install dependencies in venv
install: check-venv
    .venv/bin/pip install -r requirements.txt

# Install dev dependencies in venv
install-dev: check-venv
    .venv/bin/pip install -r requirements.txt -r requirements-dev.txt

# Run the MCP server
run: check-deps
    #!/usr/bin/env bash
    if [ ! -f .env ]; then echo "Warning: no .env file. Copy .env.example if needed"; fi
    if [ -f .env ]; then
        env $(grep -v '^#' .env | xargs) .venv/bin/python -m src.server
    else
        .venv/bin/python -m src.server
    fi

# Run tests
test: check-dev-deps
    .venv/bin/pytest

# Lint
lint: check-dev-deps
    .venv/bin/ruff check .

# Format
fmt: check-dev-deps
    .venv/bin/ruff format .

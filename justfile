# Create venv
create-venv:
    python -m venv .venv

# Install dependencies in venv
install:
    .venv/bin/pip install -r requirements.txt

# Install dev dependencies in venv
install-dev:
    .venv/bin/pip install -r requirements.txt -r requirements-dev.txt

# Run the MCP server
run:
    .venv/bin/python -m src.server

# Run tests
test:
    pytest

# Lint
lint:
    ruff check .

# Format
fmt:
    ruff format .

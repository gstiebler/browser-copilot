# Default recipe - show available commands
default:
    @just --list

# Run the Conversation Agent standalone
conversation_agent:
    uv run python -m browser_copilot.agents.conversation

# Run the REST server (main entry point)
rest-server:
    uv run rest-server

# Test the browser interaction agent standalone
browser_agent:
    uv run python -m browser_copilot.agents.browser_interaction

# Run linting and formatting
lint:
    uv run ruff check . && uv run ruff format .

# Run type checking
typecheck:
    uv run pyright src tests

# Run tests
test:
    uv run pytest

# Run pre-commit hooks
pre-commit:
    pre-commit run --all-files

# Install/sync dependencies
install:
    uv sync

# Run REST server in development mode with debug logging
dev:
    #!/usr/bin/env bash
    echo "Starting REST server in development mode..."
    CONSOLE_LOG_LEVEL=DEBUG WAIT_FOR_INPUT=true uv run rest-server

# Initial project setup
setup:
    #!/usr/bin/env bash
    uv sync
    cp -n .env.example .env || true
    echo "✅ Dependencies installed"
    echo "⚠️  Please edit .env with your API keys"

# Clean Python cache files
clean:
    #!/usr/bin/env bash
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pyright" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
    echo "✅ Cleaned Python cache files"

# Run all quality checks (lint, typecheck, test)
check:
    #!/usr/bin/env bash
    just lint
    just typecheck
    just test
    echo "✅ All checks passed!"

# Install required MCP servers
mcp-install:
    #!/usr/bin/env bash
    echo "Installing MCP servers..."
    npx @playwright/mcp@latest install
    echo "✅ MCP servers installed"

# Tail all log files
logs:
    tail -f *.log 2>/dev/null || echo 'No log files found'

# Check environment configuration
env-check:
    #!/usr/bin/env bash
    echo "Checking environment configuration..."
    [ -f .env ] || echo "❌ .env file not found"
    [ -f .env ] && grep -q "ANTHROPIC_API_KEY=." .env || echo "⚠️  ANTHROPIC_API_KEY not set"
    [ -f .env ] && grep -q "OPENROUTER_API_KEY=." .env || echo "⚠️  OPENROUTER_API_KEY not set"
    [ -f .env ] && grep -q "GEMINI_API_KEY=." .env || echo "⚠️  GEMINI_API_KEY not set"
    echo "ℹ️  At least one AI provider API key should be configured"

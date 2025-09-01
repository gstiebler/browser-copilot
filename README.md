# Browser Copilot

A Telegram bot that uses AI agents to interact with web browsers on behalf of users. It leverages MCP (Model Context Protocol) servers and Pydantic AI to perform browser automation tasks through natural language commands.

## Features

- 🤖 **AI-Powered Browser Automation**: Control web browsers using natural language
- 💬 **Telegram Bot Interface**: Easy interaction through Telegram messages
- 🏗️ **Multi-Agent Architecture**: Specialized agents for different tasks
- 📄 **PDF Processing**: Automatic handling of PDF documents
- 🧠 **Persistent Memory**: AI remembers context across sessions
- 📸 **Screenshot Capture**: Visual feedback from browser interactions
- 🔌 **Multiple AI Providers**: Support for Anthropic, OpenRouter, and Google Gemini

## Quick Start

### Prerequisites

- Python 3.11+ (see `.python-version`)
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 20+ (for MCP servers)
- [mise](https://mise.jdx.dev/) (optional, for task running)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd browser-copilot
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Create Telegram bot**
   - Message [@BotFather](https://t.me/botfather) on Telegram
   - Create a new bot and get your token
   - Add the token to `TELEGRAM_TOKEN` in `.env`

### Configuration

Required environment variables in `.env`:

```bash
# Telegram Bot
TELEGRAM_TOKEN=your_telegram_bot_token

# AI Provider (choose at least one)
ANTHROPIC_API_KEY=your_anthropic_key      # For Claude models
OPENROUTER_API_KEY=your_openrouter_key    # For various models
GEMINI_API_KEY=your_gemini_key            # For Google models

# Optional
TEMPDIR=/tmp                              # Temporary files directory
```

## Usage

### Start the Bot

```bash
# Using uv
uv run python src/telegram_bot.py

# Using mise
mise run telegram_bot

# Development mode (with debug logging)
mise run dev
```

### Telegram Commands

- `/start` - Initialize the bot
- `/help` - Show available commands
- Send any message for AI-powered responses
- Send PDFs for automatic processing

### Standalone Testing

```bash
# Test conversation agent
uv run python src/agents/conversation_agent.py

# Test browser interaction agent
uv run python src/agents/browser_interaction_agent.py
```

## Architecture

### Core Components

- **`src/telegram_bot.py`**: Main Telegram bot interface
- **`src/agents/`**: AI agent implementations
  - `conversation_agent.py`: Main orchestrator agent
  - `browser_interaction_agent.py`: Browser automation specialist
  - `page_analysis_agent.py`: Web page analysis and extraction
  - `base_agent.py`: Abstract base class for all agents

### MCP Servers

The system integrates with multiple MCP servers:

- **Playwright Browser**: Web automation and screenshots
- **Calculator**: Mathematical operations
- **PDF Server**: Document processing
- **Memory Server**: Persistent storage with reflection
- **Filesystem Server**: File operations

## Development

### Commands

```bash
# Linting and formatting
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy .

# Run all quality checks
mise run check

# Clean cache files
mise run clean
```

### Project Structure

```
src/
├── agents/              # AI agent implementations
│   ├── __init__.py
│   ├── base_agent.py
│   ├── conversation_agent.py
│   ├── browser_interaction_agent.py
│   └── page_analysis_agent.py
├── dev/                 # Development utilities
├── telegram_bot.py      # Main bot entry point
├── model_config.py      # AI model configuration
├── log_config.py        # Logging setup
└── ...                  # Other utilities
```

### Code Quality

- **Linting**: `ruff` for code formatting and style
- **Type Checking**: `mypy` for static type analysis  
- **Pre-commit**: Git hooks for automated quality checks

## Debugging

Set environment variables for debugging:

```bash
WAIT_FOR_INPUT=true          # Pause execution at key points
CONSOLE_LOG_LEVEL=DEBUG      # Verbose console output
FILE_LOG_LEVEL=DEBUG         # Detailed file logging
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run quality checks: `mise run check`
5. Submit a pull request

## Support

For issues and feature requests, please use the GitHub issue tracker.
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Browser Copilot is a Telegram bot that uses AI agents to interact with web browsers on behalf of users. It leverages MCP (Model Context Protocol) servers and Pydantic AI to perform browser automation tasks through natural language commands.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the Telegram bot
python telegram_bot.py

# Run the main test script
python main.py

# Test the pydantic MCP agent
python pydantic_mcp.py
```

## Architecture

### Core Components

1. **telegram_bot.py**: Main Telegram bot interface
   - Handles user messages and commands
   - Integrates with ConversationAgent for AI-powered responses
   - Manages lifecycle of MCP servers
`
2. **pydantic_mcp.py**: AI Agent implementation
   - ConversationAgent class manages conversation history
   - Integrates multiple MCP servers (calculator, browser automation, PDF, memory, filesystem)
   - Uses OpenRouter API for language model access
   - Handles screenshot capture and image responses

### MCP Server Integration

The system uses multiple MCP servers:
- **Calculator**: Basic mathematical operations
- **Playwright Browser**: Web browser automation and screenshots
- **PDF Server**: PDF processing capabilities
- **Memory Server**: Persistent memory storage
- **Filesystem Server**: File system operations in temp folder

### Environment Configuration

Required environment variables (.env):
- `TELEGRAM_TOKEN`: Telegram bot authentication token
- `OPENROUTER_API_KEY`: API key for OpenRouter
- `OPENROUTER_MODEL`: Model name to use (e.g., "openai/gpt-4")
- `LOGFIRE_TOKEN`: Token for Logfire monitoring

### Key Directories

- Temp folder: `~/Documents/temp/` - Used for screenshots and temporary files
- Memory storage: `~/Documents/datas/ai_memory.json` - Persistent AI memory
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Browser Copilot is a Telegram bot that uses AI agents to interact with web browsers on behalf of users. It leverages MCP (Model Context Protocol) servers and Pydantic AI to perform browser automation tasks through natural language commands.

## Development Commands

```bash
# Install dependencies using uv
uv sync

# Run the Telegram bot (main entry point)
uv run python src/telegram_bot.py

# Test the browser agent standalone
uv run python src/browser_agent.py

# Test the pydantic MCP agent
uv run python src/pydantic_mcp.py

# Run linting
uv run ruff check .
uv run ruff format .

# Run type checking
uv run mypy .

# Run tests
uv run pytest
```

## Architecture

### Core Components

1. **src/telegram_bot.py**: Main Telegram bot interface
   - Entry point for the application
   - Handles user messages, commands (/start, /help, /echo)
   - PDF document handling with automatic download
   - Integrates with ConversationAgent for AI-powered responses
   - Manages MCP server lifecycle (startup/shutdown)
   - Uses MarkdownV2 parsing for message formatting

2. **src/pydantic_mcp.py**: AI Agent implementation
   - ConversationAgent class manages conversation history
   - Integrates multiple MCP servers (calculator, browser, PDF, memory, filesystem)
   - Supports both OpenRouter (via OPENROUTER_API_KEY) and Google Gemini models
   - Handles screenshot capture and image responses
   - Implements browser_interact tool for web automation tasks

3. **src/browser_agent.py**: Specialized browser automation agent
   - BrowserAgent class specifically for Playwright MCP server
   - Handles browser navigation, screenshots, form filling, and web scraping
   - Processes screenshot nodes and returns image paths
   - Works in conjunction with ConversationAgent for browser tasks

### MCP Server Integration

The system uses multiple MCP servers:
- **Calculator** (`mcp-server-calculator`): Mathematical operations
- **Playwright Browser** (`@playwright/mcp@latest`): Web automation and screenshots
- **PDF Server** (`pdf-mcp-server`): PDF document processing
- **Memory Server** (`h-memory-mcp-server`): Persistent memory storage with reflection
- **Filesystem Server** (`@modelcontextprotocol/server-filesystem`): File operations in temp folder

### Environment Configuration

Required environment variables (.env):
- `TELEGRAM_TOKEN`: Telegram bot authentication token
- `OPENROUTER_API_KEY`: API key for OpenRouter (optional)
- `OPENROUTER_MODEL`: Model name to use (e.g., "openai/gpt-4")
- `GEMINI_API_KEY`: Google Gemini API key (used if OpenRouter not configured)
- `GEMINI_MODEL`: Gemini model name (default: "gemini-2.5-flash")
- `LOGFIRE_TOKEN`: Token for Logfire monitoring and instrumentation
- `TEMPDIR`: Temporary directory path (default: "/tmp")
- `FILE_LOG_LEVEL`: File logging level (default: "DEBUG")
- `CONSOLE_LOG_LEVEL`: Console logging level (default: "INFO")

### Key Features

- **Multi-Agent Architecture**: Separate agents for general tasks and browser-specific operations
- **Conversation Memory**: Maintains context across interactions using message history
- **Browser Automation**: Full web browser control through natural language
- **PDF Processing**: Automatic handling of PDF documents sent via Telegram
- **Persistent Memory**: AI can store and retrieve information across sessions
- **Streaming Responses**: Yields intermediate results for real-time feedback
- **Comprehensive Logging**: Colored console output and file logging with Logfire integration

### Message Flow

1. User sends message/document to Telegram bot
2. TelegramBot receives and forwards to ConversationAgent
3. ConversationAgent processes with appropriate MCP servers
4. For browser tasks, delegates to BrowserAgent via browser_interact tool
5. Results (text/images) are streamed back to user
6. Conversation history is maintained for context
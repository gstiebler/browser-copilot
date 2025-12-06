# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Browser Copilot is a REST API service with Server-Sent Events (SSE) streaming that uses AI agents to interact with web browsers on behalf of users. It leverages MCP (Model Context Protocol) servers and Pydantic AI to perform browser automation tasks through natural language commands.

## Development Commands

```bash
# Install dependencies using uv
uv sync

# Run the REST server (main entry point)
uv run rest-server
# Or use mise task runner
mise run rest-server

# Test the conversation agent
uv run python -m agents.conversation_agent
# Or use mise task runner
mise run conversation_agent

# Test the browser interaction agent standalone
uv run python -m agents.browser_interaction_agent

# Run linting
uv run ruff check .
uv run ruff format .

# Run type checking
uv run mypy .

# Run tests
uv run pytest

# Run pre-commit hooks
pre-commit run --all-files
```

## Architecture

### Core Components

1. **src/rest_server.py**: Main REST API server interface
   - Entry point for the application
   - Handles client messages via HTTP with SSE streaming
   - PDF and image document handling via file upload endpoints
   - Integrates with ConversationAgent for AI-powered responses
   - Manages MCP server lifecycle (startup/shutdown)
   - Session management for multiple concurrent clients

2. **agents/**: Agent implementations organized by responsibility
   - **base_agent.py**: Abstract base class for all agents
   - **conversation_agent.py**: Main AI agent that manages conversation history
     - Integrates multiple MCP servers (calculator, browser, PDF, memory, filesystem)
     - Supports both OpenRouter (via OPENROUTER_API_KEY) and Google Gemini models
     - Handles screenshot capture and image responses
     - Implements browser_interact tool for web automation tasks
   - **browser_interaction_agent.py**: Specialized browser automation agent
     - Handles browser navigation, screenshots, form filling, and web scraping
     - Processes screenshot nodes and returns image paths
     - Works in conjunction with ConversationAgent for browser tasks
   - **page_analysis_agent.py**: Analyzes web page structure and content
     - Performs goal-aware filtering of interactable elements based on current task
     - Takes screenshots and sends them to clients
     - Extracts structured information from web pages using accessibility tree
     - Returns formatted summaries with relevant UI elements for the given goal

3. **src/config/**: Configuration module with Pydantic models and provider logic
   - **agent_models.py**: Pydantic configuration models (AgentConfig, BrowserAgentConfig, PageAnalysisConfig)
   - **model_provider.py**: AI model provider factory (get_model function)
   - Centralized configuration for all agents and server components

### MCP Server Integration

The system uses multiple MCP servers:
- **Calculator** (`mcp-server-calculator`): Mathematical operations
- **Playwright Browser** (`@playwright/mcp@latest`): Web automation and screenshots
- **PDF Server** (`pdf-mcp-server`): PDF document processing
- **Memory Server** (`h-memory-mcp-server`): Persistent memory storage with reflection
- **Filesystem Server** (`@modelcontextprotocol/server-filesystem`): File operations in temp folder

### Environment Configuration

Required environment variables (.env):
- `REST_PORT`: Port for REST API server (default: 8000)
- `ANTHROPIC_API_KEY`: Anthropic API key for Claude models (optional)
- `OPENROUTER_API_KEY`: API key for OpenRouter (optional)
- `GEMINI_API_KEY`: Google Gemini API key (optional)
- `TEMPDIR`: Temporary directory path (default: "/tmp")
- `FILE_LOG_LEVEL`: File logging level (default: "DEBUG")
- `CONSOLE_LOG_LEVEL`: Console logging level (default: "INFO")
- `WAIT_FOR_INPUT`: If "true", pauses execution at certain points for debugging (default: "false")

Model Configuration (choose one provider):
- `MAIN_MODEL`: Main orchestrator model (e.g., "openrouter/your_model_name")
- `BROWSER_MODEL`: Model specifically for browser automation tasks
- `MEMORY_MODEL`: Model for memory-related operations

The system supports multiple AI providers:
- **Anthropic**: Direct Claude API access via ANTHROPIC_API_KEY
- **OpenRouter**: Access to various models via OPENROUTER_API_KEY
- **Google Gemini**: Via GEMINI_API_KEY

### Key Features

- **Multi-Agent Architecture**: Separate agents for general tasks and browser-specific operations
- **Conversation Memory**: Maintains context across interactions using message history
- **Browser Automation**: Full web browser control through natural language
- **PDF Processing**: Automatic handling of PDF documents via HTTP file upload
- **Persistent Memory**: AI can store and retrieve information across sessions
- **Streaming Responses**: Yields intermediate results for real-time feedback
- **Comprehensive Logging**: Colored console output and file logging with Logfire integration

### Message Flow

1. User sends message/document to REST API server via HTTP POST
2. REST server receives and forwards to ConversationAgent
3. ConversationAgent processes with appropriate MCP servers
4. For browser tasks, delegates to BrowserAgent via browser_interact tool
5. Results (text/images) are streamed back via Server-Sent Events (SSE)
6. Conversation history is maintained for context

### Development Tools

- **Task Runner**: Uses `mise` for task management (see mise.toml)
  - `mise run rest-server` - Run the REST server
  - `mise run conversation_agent` - Run the Conversation Agent standalone
  
- **Package Manager**: Uses `uv` for Python dependency management
  - Fast, Rust-based package installer
  - Manages virtual environments automatically
  - Lock file ensures reproducible builds

- **Code Quality**:
  - `ruff`: Fast Python linter and formatter
  - `mypy`: Static type checking
  - `pre-commit`: Git hooks for code quality checks

### Debugging Features

- **WAIT_FOR_INPUT**: Set to "true" to pause execution at key points
  - Useful for debugging agent decisions
  - Allows inspection of intermediate states
  - Controlled via `src/input_utils.py`

- **Logging Levels**:
  - FILE_LOG_LEVEL: Controls file logging verbosity
  - CONSOLE_LOG_LEVEL: Controls console output (uses Rich for formatting)
  - Logfire integration for production monitoring

- **Model Configuration**:
  - Supports separate models for different tasks (main, browser, memory)
  - Configurable thinking budget for Claude models
  - Multiple provider support for failover/testing

### Utility Modules

- **src/node_utils.py**: Helper for printing MCP response nodes
- **src/config/**: Centralized configuration module
  - **agent_models.py**: Pydantic configuration models
  - **model_provider.py**: AI model provider selection and instantiation
- **src/log_config.py**: Logging setup with Rich console formatting
- **src/input_utils.py**: Debug utilities for pausing execution

### Project Setup

1. **Prerequisites**:
   - Python 3.11+ (see .python-version)
   - uv package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
   - mise (optional, for task running)

2. **Initial Setup**:
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd browser-copilot
   
   # Install dependencies
   uv sync
   
   # Copy environment variables
   cp .env.example .env
   # Edit .env with your API keys and configuration
   
   # Install pre-commit hooks (optional)
   pre-commit install
   ```

3. **REST API Server Setup**:
   - Configure REST_PORT in .env (default: 8000)
   - Start the server with `uv run rest-server`
   - Connect clients to the HTTP endpoints with SSE support

### Common Issues and Solutions

- **MCP Server Errors**: If browser automation fails, the Playwright MCP server may need installation:
  ```bash
  npx @playwright/mcp@latest install
  ```

- **Model Provider Issues**: 
  - Ensure at least one API key is configured (Anthropic, OpenRouter, or Gemini)
  - Check model names match available models for your provider
  - Verify API key permissions and quotas

- **Memory/PDF Server Issues**: These are optional; the bot will work without them but with reduced functionality

### Contributing

When making changes:
1. Follow existing code patterns and conventions
2. Run linting and type checking before committing
3. Update this CLAUDE.md file if adding new features or changing architecture
4. Test both REST server and standalone agent modes
5. Run tests to ensure nothing breaks: `mise run test`

### Code Organization

- **src/**: Server infrastructure, utilities, and configuration
  - REST server, SSE streaming, logging, config models
- **agents/**: AI agent implementations
  - All agent logic and MCP server integration
- **tests/**: Test suite with unit and integration tests
  - Run with `mise run test` or `uv run pytest`
- **chat-client/**: Streamlit web UI (separate application)
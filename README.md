# Browser Copilot

A REST API service with SSE (Server-Sent Events) that uses AI agents to interact with web browsers on behalf of users. It leverages MCP (Model Context Protocol) servers and Pydantic AI to perform browser automation tasks through natural language commands.

## Features

- **AI-Powered Browser Automation**: Control web browsers using natural language
- **REST API with SSE**: Real-time streaming responses via Server-Sent Events
- **Multi-Agent Architecture**: Specialized agents for different tasks
- **PDF Processing**: Automatic handling of PDF documents
- **Persistent Memory**: AI remembers context across sessions
- **Screenshot Capture**: Visual feedback from browser interactions
- **Multiple AI Providers**: Support for Anthropic, OpenRouter, and Google Gemini
- **Session Management**: Stateful conversations with session IDs

## Quick Start

### Prerequisites

- Python 3.13+ (see `.python-version`)
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

### Configuration

Required environment variables in `.env`:

```bash
# AI Provider (choose at least one)
ANTHROPIC_API_KEY=your_anthropic_key      # For Claude models
OPENROUTER_API_KEY=your_openrouter_key    # For various models
GEMINI_API_KEY=your_gemini_key            # For Google models

# Model Configuration
MAIN_MODEL=model_name                     # Main conversation model
BROWSER_MODEL=model_name                  # Browser automation model

# Optional
TEMPDIR=/tmp                              # Temporary files directory
REST_PORT=8000                            # REST server port (default: 8000)
```

## Usage

### Start the REST Server

```bash
# Using uv
uv run rest-server

# Or directly
uv run python src/rest_server.py

# Using mise
mise run rest-server

# Development mode (with debug logging)
mise run dev
```

### REST API

The service exposes a REST API with SSE streaming. Example client usage:

```python
import json
import requests
import sseclient

# Send a message with SSE streaming
payload = {
    "session_id": "my-session-123",
    "message_type": "text",
    "content": "Navigate to example.com"
}

response = requests.post(
    "http://localhost:8000/api/message",
    json=payload,
    stream=True,
    headers={"Accept": "text/event-stream"}
)

# Parse SSE events
client = sseclient.SSEClient(response)
for event in client.events():
    if event.event == "message":
        data = json.loads(event.data)
        if "text" in data:
            print(f"Text: {data['text']}")
        elif "image" in data:
            print(f"Image: {data['image']['file_path']}")
    elif event.event == "done":
        break
```

### API Endpoints

- **POST `/api/message`**: Send a message and stream responses via SSE
- **GET `/health`**: Health check endpoint
- **DELETE `/api/session/{session_id}`**: Clean up a session

### Message Types

- **text**: Send text messages to the agent
- **image**: Send image file paths
- **pdf**: Send PDF file paths for processing

### Standalone Testing

```bash
# Test conversation agent
uv run python src/dev/console_chatbot.py

# Test browser interaction agent
uv run python src/agents/browser_interaction_agent.py
```

## Architecture

### Core Components

- **`src/rest_server.py`**: Main REST server with SSE support (FastAPI)
- **`src/sse_message_sender.py`**: Message streaming handler
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
├── rest_server.py       # Main REST server entry point
├── sse_message_sender.py  # Message streaming handler
├── model_config.py      # AI model configuration
├── log_config.py        # Logging setup
└── ...                  # Other utilities
chat-client/
├── app.py               # Streamlit chat client
└── model_config.py      # Client configuration
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

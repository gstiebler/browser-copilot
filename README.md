# Browser Copilot

A REST API service with Server-Sent Events (SSE) that uses AI agents to interact with web browsers on behalf of users. It leverages MCP (Model Context Protocol) servers and Pydantic AI to perform browser automation tasks through natural language commands.

## Features

- 🤖 **AI-Powered Browser Automation**: Control web browsers using natural language
- 🔌 **REST API with SSE**: Real-time streaming responses via Server-Sent Events
- 🏗️ **Multi-Agent Architecture**: Specialized agents for different tasks
- 📄 **PDF Processing**: Automatic handling of PDF documents via file upload
- 🧠 **Persistent Memory**: AI remembers context across sessions
- 📸 **Screenshot Capture**: Visual feedback from browser interactions
- 🌐 **Multiple AI Providers**: Support for Anthropic, OpenRouter, and Google Gemini
- 💬 **Session Management**: Stateful conversations with session IDs

## Quick Start

### Prerequisites

- Python 3.13+ (see `.python-version`)
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 20+ (for MCP servers)
- [just](https://github.com/casey/just) (optional, for task running)

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
REST_PORT=8000                            # REST API server port (default: 8000)
```

## Usage

### Start the REST Server

```bash
# Using uv
uv run rest-server

# Using just
just rest-server

# Development mode (with debug logging)
just dev
```

### REST API with SSE

The service exposes a REST API with Server-Sent Events (SSE) for streaming responses. Example client usage:

```python
import requests
import sseclient

# Server configuration
server_url = "http://localhost:8000"
session_id = "my-session-123"

# Send a message
message_data = {
    "message_type": "TEXT",
    "content": "Navigate to example.com"
}

response = requests.post(
    f"{server_url}/api/v1/sessions/{session_id}/messages",
    json=message_data,
    headers={"Accept": "text/event-stream"},
    stream=True
)

# Stream SSE responses
client = sseclient.SSEClient(response.iter_content())
for event in client.events():
    if event.event == "text":
        print(f"Text: {event.data}")
    elif event.event == "image":
        print(f"Image: {event.data}")
    elif event.event == "complete":
        break
```

### Message Types

- **TEXT**: Send text messages to the agent
- **IMAGE**: Send image file paths
- **PDF**: Send PDF file paths for processing

### Standalone Testing

```bash
# Test conversation agent
just conversation_agent

# Test browser interaction agent
just browser_agent
```

## Architecture

### Core Components

- **`src/api/server.py`**: Main REST API server with SSE streaming
- **`src/agents/`**: AI agent implementations
  - `conversation.py`: Main orchestrator agent
  - `browser_interaction.py`: Browser automation specialist
  - `page_analysis.py`: Web page analysis and extraction
  - `base.py`: Abstract base class for all agents
- **`src/config/`**: Configuration module with Pydantic models

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
uv run pyright .

# Run all quality checks
just check

# Clean cache files
just clean
```

### Project Structure

```
src/
├── browser_copilot/
│   ├── agents/          # AI agent implementations
│   │   ├── base.py
│   │   ├── conversation.py
│   │   ├── browser_interaction.py
│   │   └── page_analysis.py
│   ├── api/             # REST API server
│   │   └── server.py    # FastAPI server with SSE streaming
│   ├── config/          # Configuration module
│   │   ├── agent_models.py
│   │   └── model_provider.py
│   └── ...              # Other utilities
chat-client/             # Streamlit web UI
└── app.py               # Chat interface
```

### Code Quality

- **Linting**: `ruff` for code formatting and style
- **Type Checking**: `pyright` for static type analysis
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
4. Run quality checks: `just check`
5. Submit a pull request

## Support

For issues and feature requests, please use the GitHub issue tracker.
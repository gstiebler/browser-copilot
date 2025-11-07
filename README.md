# Browser Copilot

A gRPC service that uses AI agents to interact with web browsers on behalf of users. It leverages MCP (Model Context Protocol) servers and Pydantic AI to perform browser automation tasks through natural language commands.

## Features

- 🤖 **AI-Powered Browser Automation**: Control web browsers using natural language
- 🔌 **gRPC API**: High-performance RPC interface with server-side streaming
- 🏗️ **Multi-Agent Architecture**: Specialized agents for different tasks
- 📄 **PDF Processing**: Automatic handling of PDF documents
- 🧠 **Persistent Memory**: AI remembers context across sessions
- 📸 **Screenshot Capture**: Visual feedback from browser interactions
- 🌐 **Multiple AI Providers**: Support for Anthropic, OpenRouter, and Google Gemini
- 💬 **Session Management**: Stateful conversations with session IDs

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

3. **Generate gRPC proto files**
   ```bash
   ./generate_proto.sh
   # Or manually:
   python -m grpc_tools.protoc -I proto --python_out=proto --grpc_python_out=proto proto/browser_copilot.proto
   ```

4. **Set up environment**
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
GRPC_PORT=50051                           # gRPC server port (default: 50051)
```

## Usage

### Start the gRPC Server

```bash
# Using uv
uv run grpc-server

# Or directly
uv run python src/grpc_server.py

# Using mise
mise run grpc-server

# Development mode (with debug logging)
mise run dev
```

### gRPC API

The service exposes a gRPC API with server-side streaming. Example client usage:

```python
import grpc
import proto.browser_copilot_pb2 as pb2
import proto.browser_copilot_pb2_grpc as pb2_grpc

# Connect to server
channel = grpc.insecure_channel('localhost:50051')
stub = pb2_grpc.BrowserCopilotServiceStub(channel)

# Send a message
request = pb2.SendMessageRequest(
    session_id="my-session-123",
    message_type=pb2.MessageType.TEXT,
    content="Navigate to example.com"
)

# Stream responses
for response in stub.SendMessage(request):
    if response.text:
        print(f"Text: {response.text}")
    elif response.image:
        print(f"Image: {response.image.file_path}")
```

### Message Types

- **TEXT**: Send text messages to the agent
- **IMAGE**: Send image file paths
- **PDF**: Send PDF file paths for processing

### Standalone Testing

```bash
# Test conversation agent
uv run python src/dev/console_chatbot.py

# Test browser interaction agent
uv run python src/agents/browser_interaction_agent.py
```

## Architecture

### Core Components

- **`src/grpc_server.py`**: Main gRPC server implementation
- **`src/grpc_message_sender.py`**: Message streaming handler
- **`proto/browser_copilot.proto`**: gRPC service definition
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
├── grpc_server.py       # Main gRPC server entry point
├── grpc_message_sender.py  # Message streaming handler
├── model_config.py      # AI model configuration
├── log_config.py        # Logging setup
└── ...                  # Other utilities
proto/
├── browser_copilot.proto    # gRPC service definition
├── browser_copilot_pb2.py  # Generated message classes
└── browser_copilot_pb2_grpc.py  # Generated service classes
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
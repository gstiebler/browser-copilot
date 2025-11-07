# Browser Copilot Chat Client

A Streamlit web application for interacting with the Browser Copilot gRPC service.

## Features

- 🤖 Chat interface for browser automation commands
- 📡 Real-time streaming responses from the gRPC server
- 🔄 Session management with persistent conversation history
- ⚙️ Configurable server address
- 💬 Clean, modern UI built with Streamlit

## Prerequisites

- Python 3.10+
- Browser Copilot gRPC server running (see main README for setup)
- Dependencies installed via `uv sync` (from project root)

## Usage

### Start the gRPC Server

First, ensure the gRPC server is running:

```bash
# From project root
uv run grpc-server
# Or
mise run grpc-server
```

The server will start on `localhost:50051` by default.

### Run the Chat Client

```bash
# From project root
uv run streamlit run chat-client/app.py

# Or using mise
mise run streamlit run chat-client/app.py
```

The application will open in your default web browser at `http://localhost:8501`.

### Configuration

- **Server Address**: Configure the gRPC server address in the sidebar (default: `localhost:50051`)
- **Session ID**: Each Streamlit session gets a unique session ID for conversation continuity
- **Clear Chat**: Use the "Clear Chat History" button in the sidebar to reset the conversation

## How It Works

1. The client connects to the gRPC server using an insecure channel
2. Each message is sent as a `SendMessageRequest` with:
   - Session ID (unique per Streamlit session)
   - Message type: TEXT
   - Message content
3. Responses are streamed back and displayed in real-time
4. Conversation history is maintained in Streamlit's session state

## Troubleshooting

- **Connection errors**: Ensure the gRPC server is running and the address is correct
- **Import errors**: Make sure proto files are generated (`./generate_proto.sh`)
- **No responses**: Check server logs for errors

## Development

The chat client uses:
- `streamlit` for the web UI
- `grpcio` for gRPC communication
- Proto files from `../proto/` directory

To modify the client, edit `chat-client/app.py`.


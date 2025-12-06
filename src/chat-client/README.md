# Browser Copilot Chat Client

A Streamlit web application for interacting with the Browser Copilot REST API with SSE streaming.

## Features

- 🤖 Chat interface for browser automation commands
- 📡 Real-time streaming responses via Server-Sent Events (SSE)
- 🔄 Session management with persistent conversation history
- ⚙️ Configurable server URL
- 💬 Clean, modern UI built with Streamlit

## Prerequisites

- Python 3.13+
- Browser Copilot REST API server running (see main README for setup)
- Dependencies installed via `uv sync` (from project root)

## Usage

### Start the REST Server

First, ensure the REST API server is running:

```bash
# From project root
uv run rest-server
# Or
just rest-server
```

The server will start on `localhost:8000` by default.

### Run the Chat Client

```bash
# From project root
uv run streamlit run src/chat-client/app.py

# Or using just
just streamlit run src/chat-client/app.py
```

The application will open in your default web browser at `http://localhost:8501`.

### Configuration

- **Server URL**: Configure the REST API server URL in the sidebar (default: `http://localhost:8000`)
- **Session ID**: Each Streamlit session gets a unique session ID for conversation continuity
- **Clear Chat**: Use the "Clear Chat History" button in the sidebar to reset the conversation
- **New Session**: Start a fresh conversation with a new session ID

## How It Works

1. The client connects to the REST API server via HTTP
2. Each message is sent as a POST request to `/api/v1/sessions/{session_id}/messages` with:
   - Session ID (unique per Streamlit session)
   - Message type: TEXT
   - Message content
3. Responses are streamed back via Server-Sent Events (SSE) and displayed in real-time
4. Conversation history is maintained in Streamlit's session state

## Troubleshooting

- **Connection errors**: Ensure the REST API server is running and the URL is correct
- **No responses**: Check server logs for errors
- **SSE stream issues**: Verify the server is properly configured for Server-Sent Events

## Development

The chat client uses:
- `streamlit` for the web UI
- `requests` for HTTP communication
- `sseclient-py` for Server-Sent Events streaming

To modify the client, edit `src/chat-client/app.py`.


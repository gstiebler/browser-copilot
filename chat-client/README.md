# Browser Copilot Chat Client

A Streamlit web application for interacting with the Browser Copilot REST API with SSE streaming.

## Features

- Chat interface for browser automation commands
- Real-time streaming responses via Server-Sent Events (SSE)
- Session management with persistent conversation history
- Configurable server URL
- Clean, modern UI built with Streamlit

## Prerequisites

- Python 3.13+
- Browser Copilot REST server running (see main README for setup)
- Dependencies installed via `uv sync` (from project root)

## Usage

### Start the REST Server

First, ensure the REST server is running:

```bash
# From project root
uv run rest-server
# Or
mise run rest-server
```

The server will start on `localhost:8000` by default.

### Run the Chat Client

```bash
# From project root
uv run streamlit run chat-client/app.py

# Or using mise
mise run streamlit run chat-client/app.py
```

The application will open in your default web browser at `http://localhost:8501`.

### Configuration

- **Server URL**: Configure the REST server URL in the sidebar (default: `http://localhost:8000`)
- **Session ID**: Each Streamlit session gets a unique session ID for conversation continuity
- **Clear Chat**: Use the "Clear Chat History" button in the sidebar to reset the conversation

## How It Works

1. The client connects to the REST API server
2. Each message is sent as a POST request to `/api/message` with:
   - Session ID (unique per Streamlit session)
   - Message type: text
   - Message content
3. Responses are streamed back via SSE and displayed in real-time
4. Conversation history is maintained in Streamlit's session state

## Troubleshooting

- **Connection errors**: Ensure the REST server is running and the URL is correct
- **No responses**: Check server logs for errors

## Development

The chat client uses:
- `streamlit` for the web UI
- `requests` for HTTP communication
- `sseclient-py` for SSE event parsing

To modify the client, edit `chat-client/app.py`.

#!/usr/bin/env python3
"""Streamlit chat client for Browser Copilot REST API with SSE."""

import json
import uuid

import requests
import sseclient
import streamlit as st
from model_config import ChatClientConfig, StreamlitConfig

# Load configuration from environment
streamlit_config = StreamlitConfig.from_env()
client_config = ChatClientConfig.from_env()

# Page configuration
st.set_page_config(
    page_title=streamlit_config.page_title,
    page_icon=streamlit_config.page_icon,
    layout=streamlit_config.layout,
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "server_url" not in st.session_state:
    # Initialize server URL from config or use default
    server_address = client_config.server_address
    if ":" in server_address:
        host, port = server_address.rsplit(":", 1)
        st.session_state.server_url = f"http://{host}:{port}"
    else:
        st.session_state.server_url = "http://localhost:8000"


def check_server_connection(server_url: str) -> bool:
    """Check if the REST server is reachable.

    Args:
        server_url: Base URL of the REST server

    Returns:
        True if server is reachable, False otherwise
    """
    try:
        response = requests.get(f"{server_url}/api/v1/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def send_message(message: str) -> str:
    """Send a message to the REST server and stream SSE responses.

    Args:
        message: User message text

    Returns:
        Complete response text
    """
    server_url = st.session_state.server_url
    session_id = st.session_state.session_id

    # Prepare request data
    message_data = {"message_type": "TEXT", "content": message}

    try:
        # Create SSE request
        response = requests.post(
            f"{server_url}/api/v1/sessions/{session_id}/messages",
            json=message_data,
            headers={"Accept": "text/event-stream"},
            stream=True,
            timeout=60,
        )

        if response.status_code != 200:
            return f"Server error: {response.status_code} - {response.text}"

        # Process SSE stream
        response_text = ""
        response_placeholder = st.empty()

        client = sseclient.SSEClient(response.iter_content())  # type: ignore

        for event in client.events():
            if event.event == "text":
                chunk = event.data
                response_text += chunk
                # Update the placeholder with accumulated text
                response_placeholder.markdown(response_text)
            elif event.event == "image":
                # Handle image events
                try:
                    image_data = json.loads(event.data)
                    st.info(f"Image received: {image_data.get('file_path', 'Unknown path')}")
                except json.JSONDecodeError:
                    st.warning("Received malformed image data")
            elif event.event == "error":
                error_msg = f"Server error: {event.data}"
                st.error(error_msg)
                return response_text + f"\n\n{error_msg}"
            elif event.event == "complete":
                # Stream completed successfully
                break

        return response_text if response_text else "No response received"

    except requests.exceptions.RequestException as e:
        error_msg = f"Connection error: {str(e)}"
        st.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error sending message: {str(e)}"
        st.error(error_msg)
        return error_msg


# Sidebar configuration
with st.sidebar:
    st.title("⚙️ Configuration")
    server_url = st.text_input(
        "Server URL",
        value=st.session_state.server_url,
        help="REST API server URL (e.g., http://localhost:8000)",
    )

    # Update server URL if changed
    if server_url != st.session_state.server_url:
        st.session_state.server_url = server_url

    st.divider()

    st.subheader("Session Info")
    st.text(f"Session ID: {st.session_state.session_id[:8]}...")

    # Connection status
    if check_server_connection(st.session_state.server_url):
        st.success("🟢 Connected")
    else:
        st.error("🔴 Server not reachable")

    st.divider()

    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

    if st.button("New Session"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()


# Main chat interface
st.title("🤖 Browser Copilot Chat")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Send message and stream response
    with st.chat_message("assistant"):
        response = send_message(prompt)
        # Add assistant response to history
        st.session_state.messages.append({"role": "assistant", "content": response})

    # Rerun to update the chat display
    st.rerun()

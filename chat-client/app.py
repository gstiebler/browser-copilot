#!/usr/bin/env python3
"""Streamlit chat client for Browser Copilot REST API with SSE."""

import json
import uuid
from typing import Optional

import requests
import sseclient
import streamlit as st
from model_config import StreamlitConfig, ChatClientConfig


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
    st.session_state.server_url = client_config.server_url


def check_server_health(server_url: str) -> bool:
    """Check if the server is healthy.

    Args:
        server_url: Base URL of the server

    Returns:
        True if server is healthy, False otherwise
    """
    try:
        response = requests.get(f"{server_url}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def send_message(message: str) -> str:
    """Send a message to the REST API and stream responses via SSE.

    Args:
        message: User message text

    Returns:
        Complete response text
    """
    server_url = st.session_state.server_url

    # Create request payload
    payload = {
        "session_id": st.session_state.session_id,
        "message_type": "text",
        "content": message,
    }

    try:
        response_text = ""
        response_placeholder = st.empty()

        # Make POST request with SSE streaming
        response = requests.post(
            f"{server_url}/api/message",
            json=payload,
            stream=True,
            headers={"Accept": "text/event-stream"},
        )

        if response.status_code != 200:
            error_msg = f"Server error: {response.status_code}"
            st.error(error_msg)
            return error_msg

        # Parse SSE events
        client = sseclient.SSEClient(response)

        for event in client.events():
            if event.event == "message":
                try:
                    data = json.loads(event.data)
                    if "text" in data:
                        response_text += data["text"]
                        # Update the placeholder with accumulated text
                        response_placeholder.markdown(response_text)
                    elif "image" in data:
                        # Handle image response
                        st.info(f"Image received: {data['image']['file_path']}")
                except json.JSONDecodeError:
                    continue

            elif event.event == "error":
                try:
                    data = json.loads(event.data)
                    error_msg = data.get("error", "Unknown error")
                    st.error(f"Error: {error_msg}")
                except json.JSONDecodeError:
                    st.error("Unknown error occurred")

            elif event.event == "done":
                break

        return response_text if response_text else "No response received"

    except requests.exceptions.ConnectionError:
        error_msg = "Failed to connect to server. Please check the server URL."
        st.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error sending message: {str(e)}"
        st.error(error_msg)
        return error_msg


# Sidebar configuration
with st.sidebar:
    st.title("Configuration")
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
    if check_server_health(st.session_state.server_url):
        st.success("Connected")
    else:
        st.error("Not connected")

    st.divider()

    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()


# Main chat interface
st.title("Browser Copilot Chat")

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

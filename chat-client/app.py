#!/usr/bin/env python3
"""Streamlit chat client for Browser Copilot gRPC service."""

import sys
import uuid
from pathlib import Path
from typing import Optional, Tuple

import grpc
import streamlit as st

# Add proto directory to path
proto_path = Path(__file__).parent.parent / "proto"
if str(proto_path) not in sys.path:
    sys.path.insert(0, str(proto_path))

try:
    import browser_copilot_pb2 as pb2
    import browser_copilot_pb2_grpc as pb2_grpc
except ImportError as e:
    st.error(f"Failed to import proto files: {e}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Browser Copilot Chat",
    page_icon="🤖",
    layout="wide",
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "channel" not in st.session_state:
    st.session_state.channel = None

if "stub" not in st.session_state:
    st.session_state.stub = None

if "server_address" not in st.session_state:
    st.session_state.server_address = "localhost:50051"


def create_grpc_connection(
    server_address: str,
) -> Tuple[Optional[grpc.Channel], Optional[pb2_grpc.BrowserCopilotServiceStub]]:
    """Create gRPC channel and stub for the given server address.

    Args:
        server_address: Server address in format 'host:port'

    Returns:
        Tuple of (channel, stub) or (None, None) on error
    """
    try:
        channel = grpc.insecure_channel(server_address)
        stub = pb2_grpc.BrowserCopilotServiceStub(channel)
        return channel, stub
    except Exception as e:
        st.error(f"Failed to create gRPC connection: {e}")
        return None, None


def send_message(message: str) -> str:
    """Send a message to the gRPC server and stream responses.

    Args:
        message: User message text

    Returns:
        Complete response text
    """
    # Ensure connection is established
    if st.session_state.channel is None or st.session_state.stub is None:
        return "Not connected to server. Please check the server address in the sidebar."

    # Create request
    request = pb2.SendMessageRequest(
        session_id=st.session_state.session_id,
        message_type=pb2.MessageType.TEXT,
        content=message,
    )

    # Stream responses
    try:
        response_text = ""
        response_placeholder = st.empty()

        for response in st.session_state.stub.SendMessage(request):
            if response.HasField("text"):
                response_text += response.text
                # Update the placeholder with accumulated text
                response_placeholder.markdown(response_text)
            elif response.HasField("image"):
                # For now, we only support text, but handle image gracefully
                st.info(f"Image received: {response.image.file_path}")

        return response_text if response_text else "No response received"

    except grpc.RpcError as e:
        error_msg = f"gRPC error: {e.code()} - {e.details()}"
        st.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error sending message: {str(e)}"
        st.error(error_msg)
        return error_msg


# Sidebar configuration
with st.sidebar:
    st.title("⚙️ Configuration")
    server_address = st.text_input(
        "Server Address",
        value=st.session_state.server_address,
        help="gRPC server address in format 'host:port'",
    )

    # Update connection if server address changed
    if server_address != st.session_state.server_address:
        st.session_state.server_address = server_address
        # Close existing connection if any
        if st.session_state.channel is not None:
            try:
                st.session_state.channel.close()
            except Exception:
                pass
        # Create new connection
        channel, stub = create_grpc_connection(server_address)
        st.session_state.channel = channel
        st.session_state.stub = stub

    # Initialize connection on startup if not already connected
    if st.session_state.channel is None or st.session_state.stub is None:
        channel, stub = create_grpc_connection(st.session_state.server_address)
        st.session_state.channel = channel
        st.session_state.stub = stub

    st.divider()

    st.subheader("Session Info")
    st.text(f"Session ID: {st.session_state.session_id[:8]}...")

    # Connection status
    if st.session_state.channel is not None:
        try:
            grpc.channel_ready_future(st.session_state.channel).result(timeout=1)
            st.success("🟢 Connected")
        except Exception:
            st.warning("🟡 Connection status unknown")
    else:
        st.error("🔴 Not connected")

    st.divider()

    if st.button("Clear Chat History"):
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

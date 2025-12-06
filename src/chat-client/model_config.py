"""Pydantic model configuration for chat client."""

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ChatClientConfig(BaseModel):
    """Configuration model for chat client settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    server_address: str = "localhost:8000"
    session_id: str = ""
    auto_reconnect: bool = True
    connection_timeout: float = 5.0

    @classmethod
    def from_env(cls) -> "ChatClientConfig":
        """Load configuration from environment variables."""
        rest_port = os.getenv("REST_PORT", "8000")
        return cls(
            server_address=f"localhost:{rest_port}",
            session_id=os.getenv("SESSION_ID", ""),
            auto_reconnect=os.getenv("AUTO_RECONNECT", "true").lower() == "true",
            connection_timeout=float(os.getenv("CONNECTION_TIMEOUT", "5.0")),
        )


class MessageConfig(BaseModel):
    """Configuration model for message settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    message_type: str = "TEXT"
    max_retries: int = 3
    retry_delay: float = 1.0

    @classmethod
    def from_env(cls) -> "MessageConfig":
        """Load configuration from environment variables."""
        return cls(
            message_type=os.getenv("MESSAGE_TYPE", "TEXT"),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("RETRY_DELAY", "1.0")),
        )


class StreamlitConfig(BaseModel):
    """Configuration model for Streamlit app settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    page_title: str = "Browser Copilot Chat"
    page_icon: str = "🤖"
    layout: Literal["centered", "wide"] = "wide"

    @classmethod
    def from_env(cls) -> "StreamlitConfig":
        """Load configuration from environment variables."""
        layout_env = os.getenv("STREAMLIT_LAYOUT", "wide")
        layout: Literal["centered", "wide"] = "wide"
        if layout_env in ["centered", "wide"]:
            layout = layout_env  # type: ignore
        return cls(
            page_title=os.getenv("STREAMLIT_PAGE_TITLE", "Browser Copilot Chat"),
            page_icon=os.getenv("STREAMLIT_PAGE_ICON", "🤖"),
            layout=layout,
        )

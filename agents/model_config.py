"""Pydantic model configuration for agents."""

import os
from pydantic import BaseModel, ConfigDict, field_validator


class AgentConfig(BaseModel):
    """Configuration model for agent settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    main_model_name: str = ""
    browser_model_name: str = ""
    temp_folder: str = "/tmp"
    file_log_level: str = "DEBUG"
    console_log_level: str = "INFO"
    wait_for_input: bool = False

    @field_validator("file_log_level", mode="before")
    @classmethod
    def uppercase_log_level(cls, v: str) -> str:
        """Convert log level to uppercase."""
        if isinstance(v, str):
            return v.upper()
        return v

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load configuration from environment variables."""
        return cls(
            main_model_name=os.getenv("MAIN_MODEL", ""),
            browser_model_name=os.getenv("BROWSER_MODEL", ""),
            temp_folder=os.getenv("TEMPDIR", "/tmp"),
            file_log_level=os.getenv("FILE_LOG_LEVEL", "DEBUG").upper(),
            console_log_level=os.getenv("CONSOLE_LOG_LEVEL", "INFO").upper(),
            wait_for_input=os.getenv("WAIT_FOR_INPUT", "false").lower() == "true",
        )


class BrowserAgentConfig(BaseModel):
    """Configuration model for browser interaction agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_name: str
    output_dir: str = "/tmp"
    image_responses: str = "omit"


class PageAnalysisConfig(BaseModel):
    """Configuration model for page analysis agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_name: str
    temp_folder: str = "/tmp"

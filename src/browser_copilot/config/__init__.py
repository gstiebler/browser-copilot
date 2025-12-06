"""Configuration module for browser-copilot."""

from .logging import log_markdown, setup_logging
from .models import AgentConfig, BrowserAgentConfig, PageAnalysisConfig
from .providers import get_model

__all__ = [
    "AgentConfig",
    "BrowserAgentConfig",
    "PageAnalysisConfig",
    "get_model",
    "setup_logging",
    "log_markdown",
]

"""Configuration module for browser-copilot."""

from .agent_models import AgentConfig, BrowserAgentConfig, PageAnalysisConfig
from .model_provider import get_model

__all__ = [
    "AgentConfig",
    "BrowserAgentConfig",
    "PageAnalysisConfig",
    "get_model",
]

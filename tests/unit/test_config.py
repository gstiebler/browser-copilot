"""Test configuration models and providers."""

import pytest

from src.config import AgentConfig, BrowserAgentConfig, get_model


def test_agent_config_defaults():
    """Test AgentConfig with default values."""
    config = AgentConfig()
    assert config.temp_folder == "/tmp"
    assert config.file_log_level == "DEBUG"


def test_browser_agent_config():
    """Test BrowserAgentConfig initialization."""
    config = BrowserAgentConfig(model_name="openrouter/some-model")
    assert config.model_name == "openrouter/some-model"


def test_get_model_invalid_format():
    """Test get_model rejects invalid model name format."""
    with pytest.raises(ValueError, match="Invalid model name format"):
        get_model("test-model")


def test_get_model_unknown_provider():
    """Test get_model rejects unknown provider."""
    with pytest.raises(ValueError, match="Unknown provider"):
        get_model("unknown/model-name")

"""Shared pytest fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def temp_env(monkeypatch, tmp_path):
    """Set up temporary environment for testing."""
    monkeypatch.setenv("TEMPDIR", str(tmp_path))
    monkeypatch.setenv("WAIT_FOR_INPUT", "false")
    return tmp_path

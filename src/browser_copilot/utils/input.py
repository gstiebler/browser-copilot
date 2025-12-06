import os
from typing import Optional

# Try to import agent config, but make it optional
try:
    from ..config import AgentConfig

    _config: Optional[AgentConfig] = AgentConfig.from_env()
except ImportError:
    _config = None

# Use config if available, otherwise fall back to environment variable
WAIT_FOR_INPUT = (
    _config.wait_for_input if _config else os.getenv("WAIT_FOR_INPUT", "false").lower() == "true"
)


def wait_for_input():
    if WAIT_FOR_INPUT:
        input("Press Enter to continue...")

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown

# Try to import agent config, but make it optional
try:
    from .models import AgentConfig

    _config: Optional[AgentConfig] = AgentConfig.from_env()
except ImportError:
    _config = None

console = Console()

# Session-specific markdown log file
_session_markdown_file: Optional[Path] = None


def get_session_markdown_file() -> Path:
    """Get or create the session-specific markdown log file."""
    global _session_markdown_file
    if _session_markdown_file is None:
        # Create markdown log directory if it doesn't exist
        markdown_dir = Path("markdown_logs")
        markdown_dir.mkdir(exist_ok=True)

        # Create session-specific file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _session_markdown_file = markdown_dir / f"session_{timestamp}.md"

        # Write header to the file
        with open(_session_markdown_file, "w", encoding="utf-8") as f:
            f.write(f"# Session Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    return _session_markdown_file


def log_markdown(content: str) -> None:
    """
    Log markdown content both to console and to a session-specific markdown file.

    Args:
        content: The markdown content to log
    """
    # Log to console
    console.log(Markdown(content))

    # Write to markdown file
    markdown_file = get_session_markdown_file()
    with open(markdown_file, "a", encoding="utf-8") as f:
        # Add timestamp before each entry
        timestamp = datetime.now().strftime("%H:%M:%S")
        f.write(f"\n<!-- {timestamp} -->\n")
        f.write(content)
        f.write("\n")
        f.flush()  # Ensure content is written immediately


def setup_logging(logger_name: Optional[str] = None):
    """
    Set up logging configuration with file rotation and timestamped filenames.
    Supports different log levels for console and file output.

    Args:
        logger_name: Name of the logger. If None, configures the root logger.

    Returns:
        Logger instance

    Environment variables:
        - CONSOLE_LOG_LEVEL: Log level for console output (default: WARNING)
        - FILE_LOG_LEVEL: Log level for file output (default: DEBUG)
    """
    # Create log directory if it doesn't exist
    log_dir = "log"
    os.makedirs(log_dir, exist_ok=True)

    # Configure file logging with rotation
    log_filename = f"{log_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_conversation_agent.log"

    # Create handlers with different log levels
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    console_handler = logging.StreamHandler()

    # Set different log levels for each handler
    if _config:
        file_log_level = _config.file_log_level
        console_log_level = _config.console_log_level
    else:
        file_log_level = os.getenv("FILE_LOG_LEVEL", "DEBUG").upper()
        console_log_level = os.getenv("CONSOLE_LOG_LEVEL", "WARNING").upper()

    file_handler.setLevel(getattr(logging, file_log_level))
    console_handler.setLevel(getattr(logging, console_log_level))

    # Set format
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Get logger
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()

    # Set logger to the lowest level so handlers can filter
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

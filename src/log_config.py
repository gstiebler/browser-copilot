import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional
from rich.console import Console

console = Console()


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
    log_filename = f"{log_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_pydantic_mcp.log"

    # Create handlers with different log levels
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    console_handler = logging.StreamHandler()

    # Set different log levels for each handler
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

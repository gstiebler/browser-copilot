import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional


def setup_logging(logger_name: Optional[str] = None):
    """
    Set up logging configuration with file rotation and timestamped filenames.

    Args:
        logger_name: Name of the logger. If None, configures the root logger.

    Returns:
        Logger instance
    """
    # Create log directory if it doesn't exist
    log_dir = "log"
    os.makedirs(log_dir, exist_ok=True)

    # Configure file logging with rotation
    log_filename = f"{log_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_pydantic_mcp.log"

    # Create handlers
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    console_handler = logging.StreamHandler()

    # Set format
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Get logger
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()

    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

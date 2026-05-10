"""
Logging Utility
Provides a standardized logger configuration for the application.
"""

import logging
import sys
from pathlib import Path


# reference documentation:
# https://realpython.com/python-logging/
def setup_logger(
    name: str = "Tracker", log_level: int = logging.INFO
) -> logging.Logger:
    """
    Sets up a logger with both console and file handlers.

    :param name: The name of the logger.
    :param log_level: The logging level (e.g., logging.INFO, logging.DEBUG).
    :return: A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    if logger.hasHandlers():
        logger.setLevel(log_level)
        return logger

    logger.setLevel(log_level)

    # Define the format
    formatter = logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d | %(levelname)-8s "
        "| [%(module)s.%(funcName)s:%(lineno)d] | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_path = log_dir / f"{name}.log"
    file_handler = logging.FileHandler(file_path, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

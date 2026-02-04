"""Shared utility functions for all agents."""

import logging
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


def setup_logging(name: str = "po_assistant", level: int = logging.INFO) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create console handler with formatting
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def load_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables.

    Returns:
        Configuration dictionary
    """
    # Load .env file
    load_dotenv()

    # Get API keys and settings
    config = {
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        "model": os.getenv("MODEL", "claude-3-5-sonnet-20241022"),
        "temperature": float(os.getenv("TEMPERATURE", "0.7")),
        "max_tokens": int(os.getenv("MAX_TOKENS", "4096")),
        "data_dir": Path(os.getenv("DATA_DIR", "data")),
        "output_dir": Path(os.getenv("OUTPUT_DIR", "data/outputs")),
    }

    # Validate required settings
    if not config["anthropic_api_key"]:
        raise ValueError(
            "ANTHROPIC_API_KEY not found in environment variables. "
            "Please create a .env file based on .env.example"
        )

    return config


# Create default logger
logger = setup_logging()

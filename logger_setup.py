"""Logging configuration with rotating file handler."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .platform_utils import get_log_dir


_CONFIGURED = False


def setup_logging(
    level: str = "INFO",
    log_dir: Optional[Path] = None,
) -> logging.Logger:
    """Configure application-wide logging with file and console handlers."""
    global _CONFIGURED
    if _CONFIGURED:
        return logging.getLogger("gui_builder")

    log_dir = log_dir or get_log_dir()
    log_file = log_dir / "gui_builder.log"

    root_logger = logging.getLogger("gui_builder")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    _CONFIGURED = True
    return root_logger


def get_recent_errors(max_count: int = 50) -> list[str]:
    """Read recent error lines from the log file."""
    log_file = get_log_dir() / "gui_builder.log"
    if not log_file.exists():
        return []
    errors: list[str] = []
    try:
        for line in log_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if "| ERROR" in line or "| WARNING" in line:
                errors.append(line)
        return errors[-max_count:]
    except OSError:
        return []

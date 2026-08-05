"""Application-wide structured logging.

Wraps `loguru <https://github.com/Delgan/loguru>`_ to provide a single
``configure_logging`` entry point (called once at process start) and a
``get_logger`` factory that every module uses to obtain a named, bound
logger. Centralizing this here means log formatting, rotation, and level
policy can change in one place without touching call sites.
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger as _logger

from app.config import LOGS_DIR, get_settings

_CONFIGURED: bool = False

_CONSOLE_FORMAT = (
    "<dim>{time:YYYY-MM-DD HH:mm:ss}</dim> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
    "- <level>{message}</level>"
)

_FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"


def configure_logging(log_dir: Path | None = None) -> None:
    """Configure the global loguru sinks (console + rotating file).

    Idempotent: subsequent calls are no-ops so importing this module from
    several places (agent, UI, tools) never duplicates log sinks.

    Args:
        log_dir: Directory rotating log files are written to. Defaults to
            the project's ``logs/`` directory.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    target_dir = log_dir or LOGS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    _logger.remove()
    _logger.add(
        sys.stderr,
        level=settings.log_level,
        format=_CONSOLE_FORMAT,
        colorize=True,
        backtrace=False,
        diagnose=settings.debug,
    )
    _logger.add(
        target_dir / "travel_agent.log",
        level="DEBUG",
        format=_FILE_FORMAT,
        rotation="5 MB",
        retention=5,
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )
    _CONFIGURED = True


def get_logger(name: str):
    """Return a loguru logger bound to ``name`` (typically ``__name__``).

    Ensures :func:`configure_logging` has run before handing back the
    logger, so any module can simply do
    ``logger = get_logger(__name__)`` without worrying about init order.

    Args:
        name: Identifier shown in the ``name`` field of every log line,
            conventionally the importing module's ``__name__``.

    Returns:
        A loguru logger instance bound with the given name.
    """
    configure_logging()
    return _logger.bind(name=name)

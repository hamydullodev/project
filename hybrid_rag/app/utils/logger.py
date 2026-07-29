"""
Application-wide logging setup.

WHY THIS MODULE EXISTS
-----------------------
The spec requires logging every stage of the pipeline: ingestion, embedding,
search, reranking, generation, and errors. If every module configured its
own handlers, we'd get duplicate log lines, inconsistent formats, and no
single file to `tail -f` while debugging. This module configures Python's
standard `logging` package ONE time, at process startup, and every other
module just calls `get_logger(__name__)` to get a properly-configured
logger for free.

HOW IT WORKS INTERNALLY
------------------------
Python's `logging` module has a tree of loggers rooted at the "root"
logger. `setup_logging()` attaches two handlers to the root logger:

  1. A `StreamHandler` writing to the console (stdout) — for interactive
     development, so you see log lines as you work.
  2. A `RotatingFileHandler` writing to `logs/app.log` — for a durable,
     inspectable record, capped in size so it can't grow unboundedly. When
     the file exceeds `maxBytes`, it's rotated to `app.log.1`, and up to
     `backupCount` old rotations are kept before the oldest is deleted.

Because every module calls `logging.getLogger(__name__)` (via our
`get_logger` wrapper), log records automatically inherit the module's
dotted path as their logger name (e.g. `app.ingestion.pdf_loader`), and
propagate up to the root logger's handlers — we never attach handlers to
child loggers directly, avoiding duplicate log lines.

`setup_logging()` is idempotent: calling it more than once (e.g. once from
`run.py` and again from a Streamlit page re-run) does not create duplicate
handlers, because we clear existing handlers on the root logger first.

TIME / MEMORY COMPLEXITY
-------------------------
O(1) setup cost. Per-log-call cost is O(1) (format a string, write a line);
the rotating file handler's rotation check is O(1) per write (a file-size
stat), with the occasional O(file size) cost of the rotation itself.

ADVANTAGES
-----------
- One configuration point; consistent format everywhere.
- Durable, size-capped log file survives process restarts for later
  debugging, without needing an external log aggregation service.
- Per-module logger names make it trivial to filter/grep by subsystem.

DISADVANTAGES
--------------
- Single log file mixes all subsystems together (ingestion, retrieval,
  generation); for a bigger system you'd want structured/JSON logs shipped
  to something like Loki or Elasticsearch instead of a flat text file.
- Log rotation is size-based, not time-based; if you need "one file per
  day", swap `RotatingFileHandler` for `TimedRotatingFileHandler`.

ALTERNATIVES CONSIDERED
-------------------------
- `structlog` / JSON logging: better for machine parsing, overkill for a
  local single-user educational project where a human reads the log file.
- `print()` statements: no levels, no timestamps, no file persistence, no
  way to silence noisy modules independently.

BEST PRACTICES APPLIED
------------------------
- Configure logging once, at the application's entry point, not inside
  library modules (library modules only ever call `getLogger`, never
  `basicConfig` or add handlers themselves).
- Include timestamp, level, logger name, and message in every line — the
  minimum needed to answer "what happened, where, and when" during
  debugging.
- Log level is configurable via `.env` (`LOG_LEVEL`), so you can flip to
  DEBUG without touching code.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.config import settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per log file before rotating
_BACKUP_COUNT = 5  # keep app.log.1 .. app.log.5 before deleting the oldest

_configured = False


def setup_logging() -> None:
    """Attach console + rotating-file handlers to the root logger.

    Safe to call multiple times — subsequent calls are no-ops, so any
    module can call this defensively without worrying about duplicate
    handlers (and therefore duplicate log lines).
    """
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(settings.log_level)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(formatter)

    log_file = settings.log_dir_resolved / "app.log"
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    # Clear any pre-existing handlers (e.g. from a prior setup_logging call
    # in the same process, or a library that called logging.basicConfig)
    # before attaching ours, so we never end up with duplicate log lines.
    root.handlers.clear()
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    # Third-party libraries (huggingface, urllib3, etc.) are often very
    # chatty at INFO/DEBUG. Cap them at WARNING so our own log lines aren't
    # drowned out, unless the user explicitly asked for DEBUG everywhere.
    if settings.log_level != "DEBUG":
        for noisy_logger in ("urllib3", "httpx", "sentence_transformers", "transformers"):
            logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    _configured = True
    logging.getLogger(__name__).info(
        "Logging initialized. level=%s file=%s", settings.log_level, log_file
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger for `name`, ensuring logging has been configured.

    Every module in this project should call `get_logger(__name__)` at
    module scope rather than `logging.getLogger(__name__)` directly — this
    guarantees `setup_logging()` has run even if the module is imported
    before `run.py`'s entry point executes (e.g. in a unit test).
    """
    setup_logging()
    return logging.getLogger(name)

from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config import Config

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# Uvicorn configures these loggers with propagate=False and their own StreamHandlers.
# We need to route them through root so they reach the file handler too.
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.access", "uvicorn.error")


def setup_file_logging(cfg: "Config") -> None:
    """Configure unified logging from cfg.

    Always applies the root logger level from cfg.log_level. When log_file is set:
    - Adds a RotatingFileHandler so logs persist to disk.
    - Adds a StreamHandler if none exists (the uvicorn/api process does not call
      basicConfig, so without this, application logs never reach stdout).
    - Re-routes uvicorn's loggers through root (sets propagate=True, removes their
      own StreamHandlers) so HTTP access/error logs appear in both stdout and file,
      matching what `docker compose logs -f` shows.

    Safe to call multiple times — skips handler setup if the same file is already registered.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, cfg.log_level.upper(), logging.INFO))

    if not cfg.log_file:
        return

    from logging.handlers import RotatingFileHandler

    abs_path = os.path.abspath(cfg.log_file)

    for handler in root.handlers:
        if (
            isinstance(handler, RotatingFileHandler)
            and os.path.abspath(handler.baseFilename) == abs_path
        ):
            return  # already registered

    formatter = logging.Formatter(_LOG_FORMAT)

    fh = RotatingFileHandler(
        abs_path,
        maxBytes=cfg.log_max_bytes,
        backupCount=cfg.log_backup_count,
        encoding="utf-8",
    )
    fh.setFormatter(formatter)
    root.addHandler(fh)

    # The uvicorn/api process never calls basicConfig, so root has no StreamHandler.
    # Add one so application logs (from route handlers etc.) reach stdout and thus
    # appear in `docker compose logs -f`.
    has_stream = any(
        isinstance(h, logging.StreamHandler)
        and not isinstance(h, RotatingFileHandler)
        for h in root.handlers
    )
    if not has_stream:
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(formatter)
        root.addHandler(sh)

    # Route uvicorn's loggers through root. Remove their own StreamHandlers first
    # to avoid duplicating each line on stdout.
    for name in _UVICORN_LOGGERS:
        uv = logging.getLogger(name)
        uv.handlers = [h for h in uv.handlers if not isinstance(h, logging.StreamHandler)]
        uv.propagate = True

    logging.getLogger(__name__).info("File logging enabled: %s", abs_path)

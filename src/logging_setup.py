from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config import Config

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_file_logging(cfg: "Config") -> None:
    """Add a RotatingFileHandler to the root logger if log_file is configured.

    Safe to call multiple times — skips setup if a handler for the same file
    already exists (prevents duplicate log entries on uvicorn hot-reload).
    """
    if not cfg.log_file:
        return

    from logging.handlers import RotatingFileHandler

    abs_path = os.path.abspath(cfg.log_file)
    root = logging.getLogger()

    for handler in root.handlers:
        if (
            isinstance(handler, RotatingFileHandler)
            and os.path.abspath(handler.baseFilename) == abs_path
        ):
            return  # already registered

    fh = RotatingFileHandler(
        abs_path,
        maxBytes=cfg.log_max_bytes,
        backupCount=cfg.log_backup_count,
        encoding="utf-8",
    )
    fh.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(fh)
    logging.getLogger(__name__).info("File logging enabled: %s", abs_path)

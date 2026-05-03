from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config import Config

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_file_logging(cfg: "Config") -> None:
    """Set the root logger level from config and, if log_file is configured,
    attach a RotatingFileHandler.

    Safe to call multiple times — skips handler registration if one for the
    same file already exists (prevents duplicate entries on uvicorn hot-reload).
    The root logger level is always applied so that INFO/DEBUG messages are not
    silently dropped when no basicConfig call precedes this (e.g. the API server
    path which skips logging.basicConfig).
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

    fh = RotatingFileHandler(
        abs_path,
        maxBytes=cfg.log_max_bytes,
        backupCount=cfg.log_backup_count,
        encoding="utf-8",
    )
    fh.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(fh)
    logging.getLogger(__name__).info("File logging enabled: %s", abs_path)

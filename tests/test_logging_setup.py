"""Tests for src/logging_setup.setup_file_logging."""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from unittest.mock import MagicMock

import pytest

from src.logging_setup import setup_file_logging


def _make_cfg(log_file: str = "", log_max_bytes: int = 1024, log_backup_count: int = 1):
    cfg = MagicMock()
    cfg.log_file = log_file
    cfg.log_max_bytes = log_max_bytes
    cfg.log_backup_count = log_backup_count
    return cfg


def _rfh_count_for(abs_path: str) -> int:
    root = logging.getLogger()
    return sum(
        1
        for h in root.handlers
        if isinstance(h, RotatingFileHandler)
        and os.path.abspath(h.baseFilename) == abs_path
    )


@pytest.fixture(autouse=True)
def _clean_root_handlers():
    """Remove RotatingFileHandlers added during a test so they don't bleed across tests."""
    yield
    root = logging.getLogger()
    for h in list(root.handlers):
        if isinstance(h, RotatingFileHandler):
            h.close()
            root.removeHandler(h)


def test_empty_log_file_adds_no_handler():
    root = logging.getLogger()
    before = len(root.handlers)
    setup_file_logging(_make_cfg(log_file=""))
    assert len(root.handlers) == before


def test_configured_log_file_adds_rotating_handler(tmp_path):
    log_path = str(tmp_path / "app.log")
    setup_file_logging(_make_cfg(log_file=log_path))
    assert _rfh_count_for(log_path) == 1


def test_handler_uses_configured_max_bytes(tmp_path):
    log_path = str(tmp_path / "app.log")
    setup_file_logging(_make_cfg(log_file=log_path, log_max_bytes=2048))
    root = logging.getLogger()
    handlers = [
        h for h in root.handlers
        if isinstance(h, RotatingFileHandler)
        and os.path.abspath(h.baseFilename) == os.path.abspath(log_path)
    ]
    assert handlers[0].maxBytes == 2048


def test_handler_uses_configured_backup_count(tmp_path):
    log_path = str(tmp_path / "app.log")
    setup_file_logging(_make_cfg(log_file=log_path, log_backup_count=5))
    root = logging.getLogger()
    handlers = [
        h for h in root.handlers
        if isinstance(h, RotatingFileHandler)
        and os.path.abspath(h.baseFilename) == os.path.abspath(log_path)
    ]
    assert handlers[0].backupCount == 5


def test_idempotent_second_call_does_not_duplicate_handler(tmp_path):
    log_path = str(tmp_path / "dedup.log")
    cfg = _make_cfg(log_file=log_path)
    setup_file_logging(cfg)
    setup_file_logging(cfg)
    assert _rfh_count_for(log_path) == 1


def test_different_files_get_separate_handlers(tmp_path):
    path_a = str(tmp_path / "a.log")
    path_b = str(tmp_path / "b.log")
    setup_file_logging(_make_cfg(log_file=path_a))
    setup_file_logging(_make_cfg(log_file=path_b))
    assert _rfh_count_for(path_a) == 1
    assert _rfh_count_for(path_b) == 1

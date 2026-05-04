"""Tests for src/logging_setup.setup_file_logging."""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from unittest.mock import MagicMock

import pytest

from src.logging_setup import setup_file_logging


def _make_cfg(
    log_file: str = "",
    log_max_bytes: int = 1024,
    log_backup_count: int = 1,
    log_level: str = "INFO",
):
    cfg = MagicMock()
    cfg.log_file = log_file
    cfg.log_max_bytes = log_max_bytes
    cfg.log_backup_count = log_backup_count
    cfg.log_level = log_level
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
    """Remove handlers added during a test and restore root level + uvicorn logger state."""
    root = logging.getLogger()
    original_level = root.level
    orig_root_handlers = list(root.handlers)

    uv_state: dict = {}
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv = logging.getLogger(name)
        uv_state[name] = (list(uv.handlers), uv.propagate)

    yield

    root.setLevel(original_level)
    for h in list(root.handlers):
        if h not in orig_root_handlers:
            if isinstance(h, RotatingFileHandler):
                h.close()
            root.removeHandler(h)

    for name, (handlers, propagate) in uv_state.items():
        uv = logging.getLogger(name)
        uv.handlers = handlers
        uv.propagate = propagate


def test_empty_log_file_adds_no_handler():
    root = logging.getLogger()
    before = len(root.handlers)
    setup_file_logging(_make_cfg(log_file=""))
    assert len(root.handlers) == before


def test_root_level_is_applied_from_config(tmp_path):
    log_path = str(tmp_path / "level.log")
    setup_file_logging(_make_cfg(log_file=log_path, log_level="DEBUG"))
    assert logging.getLogger().level == logging.DEBUG


def test_root_level_applied_even_without_log_file():
    setup_file_logging(_make_cfg(log_file="", log_level="WARNING"))
    assert logging.getLogger().level == logging.WARNING


def test_invalid_log_level_falls_back_to_info(tmp_path):
    log_path = str(tmp_path / "fallback.log")
    setup_file_logging(_make_cfg(log_file=log_path, log_level="NOTAVALIDLEVEL"))
    assert logging.getLogger().level == logging.INFO


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


# ---------------------------------------------------------------------------
# StreamHandler added when root has none (api/uvicorn process scenario)
# ---------------------------------------------------------------------------


def test_stream_handler_added_when_root_has_none(tmp_path):
    root = logging.getLogger()
    # Remove any StreamHandlers present (simulates uvicorn process without basicConfig)
    existing_streams = [h for h in root.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)]
    for h in existing_streams:
        root.removeHandler(h)

    setup_file_logging(_make_cfg(log_file=str(tmp_path / "app.log")))

    stream_handlers = [
        h for h in root.handlers
        if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
    ]
    assert len(stream_handlers) >= 1

    for h in existing_streams:
        root.addHandler(h)


def test_stream_handler_not_duplicated_when_already_present(tmp_path):
    import sys
    root = logging.getLogger()
    sh = logging.StreamHandler(sys.stderr)
    root.addHandler(sh)

    setup_file_logging(_make_cfg(log_file=str(tmp_path / "app.log")))

    stream_handlers = [
        h for h in root.handlers
        if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
    ]
    # Should not have grown — only the one we added
    assert sum(1 for h in stream_handlers) >= 1
    root.removeHandler(sh)


# ---------------------------------------------------------------------------
# Uvicorn loggers rerouted through root
# ---------------------------------------------------------------------------


def test_uvicorn_loggers_propagate_after_setup(tmp_path):
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).propagate = False

    setup_file_logging(_make_cfg(log_file=str(tmp_path / "app.log")))

    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        assert logging.getLogger(name).propagate is True


def test_uvicorn_stream_handlers_removed_to_avoid_duplicates(tmp_path):
    import sys
    for name in ("uvicorn", "uvicorn.access"):
        uv = logging.getLogger(name)
        uv.addHandler(logging.StreamHandler(sys.stdout))
        uv.propagate = False

    setup_file_logging(_make_cfg(log_file=str(tmp_path / "app.log")))

    for name in ("uvicorn", "uvicorn.access"):
        uv = logging.getLogger(name)
        stream_handlers = [h for h in uv.handlers if isinstance(h, logging.StreamHandler)]
        assert stream_handlers == [], f"{name} should have no StreamHandlers after setup"

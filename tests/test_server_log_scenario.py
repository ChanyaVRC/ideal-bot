"""Integration scenario: messages emitted via the logging module appear in
GET /api/admin/server-logs.

Each test exercises the full pipeline:
  1. The app lifespan calls setup_file_logging, which attaches a
     RotatingFileHandler and sets the root logger level from cfg.log_level.
  2. Code (the test itself) emits messages via logging.getLogger(...).
  3. GET /api/admin/server-logs reads the file with _tail_lines and returns
     the lines in the JSON response.

This is a regression guard for the bug where the root logger level was
never set in the API server path, so INFO/DEBUG messages were silently
dropped before reaching the file handler.
"""
from __future__ import annotations

import logging
import pathlib
from logging.handlers import RotatingFileHandler

import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.api.deps import require_auth
from src.config import Config
from src.db.connection import init_schema, open_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _flush_file_handlers() -> None:
    """Flush RotatingFileHandlers so logged content is on disk before the API reads it."""
    for h in logging.getLogger().handlers:
        if isinstance(h, RotatingFileHandler):
            h.flush()


def _make_cfg(tmp_path, *, log_level: str = "DEBUG") -> Config:
    return Config(
        discord_token="test-token",
        encryption_master_key=Fernet.generate_key().decode(),
        session_secret="test-secret-key-at-least-32-chars!!",
        discord_client_id="test-client-id",
        discord_client_secret="test-client-secret",
        discord_redirect_uri="http://localhost:8000/auth/callback",
        bot_admin_ids=["111111111111111111"],
        db_path=str(tmp_path / "test.db"),
        frontend_url="http://localhost:5173",
        log_file=str(tmp_path / "bot.log"),
        log_level=log_level,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _restore_root_logging():
    """Restore root logger level and remove file handlers added during a test."""
    root = logging.getLogger()
    original_level = root.level
    yield
    root.setLevel(original_level)
    for h in list(root.handlers):
        if isinstance(h, RotatingFileHandler):
            h.close()
            root.removeHandler(h)


@pytest.fixture
async def log_client(tmp_path):
    """Admin API client with file logging activated.

    Yields (client, logger, cfg) so tests can emit messages and assert on
    what the API returns.  log_level is set to DEBUG so all levels are
    captured; level-filtering is tested separately via _make_cfg directly.

    setup_file_logging is called explicitly here because ASGITransport does
    not trigger the ASGI lifespan, so we cannot rely on the lifespan to set
    up the file handler.
    """
    from src.logging_setup import setup_file_logging

    cfg = _make_cfg(tmp_path, log_level="DEBUG")
    setup_file_logging(cfg)

    app = create_app(cfg)
    db = await open_db(cfg.db_path)
    await init_schema(db)
    app.state.cfg = cfg
    app.state.db = db

    async def _mock_admin():
        return {"user_id": "111111111111111111", "username": "admin", "is_bot_admin": True}

    app.dependency_overrides[require_auth] = _mock_admin

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c, logging.getLogger("test.scenario"), cfg
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# Scenario tests
# ---------------------------------------------------------------------------


class TestServerLogScenario:
    """Logged messages must be retrievable via GET /api/admin/server-logs."""

    async def test_info_message_appears_in_response(self, log_client):
        client, logger, _ = log_client
        logger.info("hello from scenario test")
        _flush_file_handlers()

        r = await client.get("/api/admin/server-logs?lines=200")

        assert r.status_code == 200
        data = r.json()
        assert data["available"] is True
        assert any("hello from scenario test" in line for line in data["lines"])

    async def test_warning_line_contains_level_tag(self, log_client):
        """The formatter must include [WARNING] so the frontend can colorize it."""
        client, logger, _ = log_client
        logger.warning("watch out from scenario test")
        _flush_file_handlers()

        r = await client.get("/api/admin/server-logs?lines=200")
        lines = r.json()["lines"]

        matching = [l for l in lines if "watch out from scenario test" in l]
        assert matching, "WARNING message not found in response"
        assert "[WARNING]" in matching[0]

    async def test_error_line_contains_level_tag(self, log_client):
        client, logger, _ = log_client
        logger.error("something broke in scenario test")
        _flush_file_handlers()

        r = await client.get("/api/admin/server-logs?lines=200")
        lines = r.json()["lines"]

        matching = [l for l in lines if "something broke in scenario test" in l]
        assert matching, "ERROR message not found in response"
        assert "[ERROR]" in matching[0]

    async def test_all_levels_present_when_log_level_is_debug(self, log_client):
        client, logger, _ = log_client
        logger.debug("multi-level debug")
        logger.info("multi-level info")
        logger.warning("multi-level warning")
        logger.error("multi-level error")
        _flush_file_handlers()

        r = await client.get("/api/admin/server-logs?lines=200")
        lines = r.json()["lines"]

        for expected in (
            "multi-level debug",
            "multi-level info",
            "multi-level warning",
            "multi-level error",
        ):
            assert any(expected in l for l in lines), f"Expected '{expected}' in log lines"

    async def test_debug_suppressed_when_log_level_is_info(self, tmp_path):
        """Messages below log_level must not reach the file."""
        from src.logging_setup import setup_file_logging

        cfg = _make_cfg(tmp_path, log_level="INFO")
        setup_file_logging(cfg)

        app = create_app(cfg)
        db = await open_db(cfg.db_path)
        await init_schema(db)
        app.state.cfg = cfg
        app.state.db = db

        async def _mock_admin():
            return {"user_id": "111111111111111111", "username": "admin", "is_bot_admin": True}

        app.dependency_overrides[require_auth] = _mock_admin
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                log = logging.getLogger("test.level_check")
                log.debug("suppressed debug message")
                log.info("visible info message")
                _flush_file_handlers()

                r = await c.get("/api/admin/server-logs?lines=200")
        finally:
            await db.close()

        lines = r.json()["lines"]
        assert any("visible info message" in l for l in lines)
        assert not any("suppressed debug message" in l for l in lines)

    async def test_lines_param_returns_tail(self, log_client):
        """lines=N must return at most N lines and they must be the most recent ones."""
        client, logger, _ = log_client
        for i in range(20):
            logger.info("entry %d", i)
        _flush_file_handlers()

        r = await client.get("/api/admin/server-logs?lines=5")
        data = r.json()

        assert len(data["lines"]) <= 5
        assert any("entry 19" in l for l in data["lines"])

    async def test_size_bytes_matches_file_on_disk(self, log_client):
        client, logger, cfg = log_client
        logger.info("sizing test message")
        _flush_file_handlers()

        on_disk = pathlib.Path(cfg.log_file).stat().st_size
        r = await client.get("/api/admin/server-logs")

        assert r.json()["size_bytes"] == on_disk

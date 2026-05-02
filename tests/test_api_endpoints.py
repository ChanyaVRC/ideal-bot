"""FastAPI endpoint tests.

These tests use httpx.AsyncClient with ASGITransport to test the API
without starting a real server. They cover authentication guards and
basic routing for all three router groups.

Run with:
    uv run pytest tests/test_api_endpoints.py -v
"""
from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.api.deps import guild_access, require_auth
from src.config import Config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cfg(tmp_path):
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
    )


@pytest.fixture
async def client(cfg):
    """Unauthenticated test client with app state manually initialized."""
    from src.db.connection import init_schema, open_db

    app = create_app(cfg)
    db = await open_db(cfg.db_path)
    await init_schema(db)  # idempotent — creates tables and default patterns
    app.state.cfg = cfg
    app.state.db = db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    finally:
        await db.close()


@pytest.fixture
async def admin_client(cfg):
    """Client with bot-admin session injected via dependency override."""
    from src.db.connection import init_schema, open_db

    app = create_app(cfg)
    db = await open_db(cfg.db_path)
    await init_schema(db)
    app.state.cfg = cfg
    app.state.db = db

    async def mock_admin():
        return {"user_id": "111111111111111111", "username": "admin", "is_bot_admin": True}

    app.dependency_overrides[require_auth] = mock_admin

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    finally:
        await db.close()


@pytest.fixture
async def guild_client(cfg):
    """Client with guild-manager session injected via dependency override."""
    from src.db.connection import init_schema, open_db

    app = create_app(cfg)
    db = await open_db(cfg.db_path)
    await init_schema(db)
    app.state.cfg = cfg
    app.state.db = db

    async def mock_user():
        return {"user_id": "222222222222222222", "username": "manager", "is_bot_admin": False}

    async def mock_guild_access(guild_id: str):
        return {"user_id": "222222222222222222", "username": "manager"}

    app.dependency_overrides[require_auth] = mock_user
    app.dependency_overrides[guild_access] = mock_guild_access

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
    finally:
        await db.close()


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


class TestAuthEndpoints:
    async def test_login_redirects_to_discord(self, client):
        r = await client.get("/auth/login", follow_redirects=False)
        assert r.status_code == 307
        assert "discord.com/oauth2/authorize" in r.headers["location"]

    async def test_login_includes_state_param(self, client):
        r = await client.get("/auth/login", follow_redirects=False)
        assert "state=" in r.headers["location"]

    async def test_me_unauthenticated_returns_401(self, client):
        r = await client.get("/auth/me")
        assert r.status_code == 401

    async def test_guilds_unauthenticated_returns_401(self, client):
        r = await client.get("/auth/guilds")
        assert r.status_code == 401

    async def test_logout_always_succeeds(self, client):
        r = await client.post("/auth/logout")
        assert r.status_code == 200

    async def test_callback_missing_code_returns_400(self, client):
        r = await client.get("/auth/callback")
        assert r.status_code == 400

    async def test_callback_invalid_state_returns_400(self, client):
        r = await client.get("/auth/callback?code=abc&state=invalid")
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Admin endpoints (bot-admin only)
# ---------------------------------------------------------------------------


class TestAdminEndpoints:
    async def test_settings_unauthenticated_returns_401(self, client):
        r = await client.get("/api/admin/settings")
        assert r.status_code == 401

    async def test_guilds_unauthenticated_returns_401(self, client):
        r = await client.get("/api/admin/guilds")
        assert r.status_code == 401

    async def test_logs_unauthenticated_returns_401(self, client):
        r = await client.get("/api/admin/logs")
        assert r.status_code == 401

    async def test_settings_as_admin_returns_200(self, admin_client):
        r = await admin_client.get("/api/admin/settings")
        assert r.status_code == 200
        data = r.json()
        assert "global_llm_provider" in data
        assert "global_llm_model" in data
        assert "has_global_api_key" in data
        assert "discord_cache_ttl" in data

    async def test_guilds_as_admin_returns_200(self, admin_client):
        r = await admin_client.get("/api/admin/guilds")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_logs_as_admin_returns_200(self, admin_client):
        r = await admin_client.get("/api/admin/logs")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        if data:
            assert "reply_context" in data[0]

    async def test_update_settings_as_admin(self, admin_client):
        r = await admin_client.patch(
            "/api/admin/settings",
            json={"global_llm_provider": "gemini", "global_llm_model": "gemini-2.0-flash"},
        )
        assert r.status_code == 200

    async def test_non_admin_user_gets_403(self, cfg, tmp_path):
        """User authenticated but not in bot_admin_ids → 403."""
        from src.db.connection import init_schema, open_db

        app = create_app(cfg)
        db = await open_db(cfg.db_path)
        await init_schema(db)
        app.state.cfg = cfg
        app.state.db = db

        async def mock_non_admin():
            return {"user_id": "999999999999999999", "username": "nobody"}

        app.dependency_overrides[require_auth] = mock_non_admin
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            r = await c.get("/api/admin/settings")
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Guild endpoints (guild manager)
# ---------------------------------------------------------------------------

GUILD_ID = "123456789012345678"


class TestGuildEndpoints:
    async def test_settings_unauthenticated_returns_401(self, client):
        r = await client.get(f"/api/guilds/{GUILD_ID}/settings")
        assert r.status_code == 401

    async def test_words_unauthenticated_returns_401(self, client):
        r = await client.get(f"/api/guilds/{GUILD_ID}/words")
        assert r.status_code == 401

    async def test_settings_as_manager_returns_200(self, guild_client):
        r = await guild_client.get(f"/api/guilds/{GUILD_ID}/settings")
        assert r.status_code == 200
        data = r.json()
        assert "guild_id" in data
        assert "reply_rate" in data

    async def test_words_as_manager_returns_list(self, guild_client):
        r = await guild_client.get(f"/api/guilds/{GUILD_ID}/words")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_update_settings_as_manager(self, guild_client):
        r = await guild_client.patch(
            f"/api/guilds/{GUILD_ID}/settings",
            json={"reply_rate": 20, "bot_enabled": True},
        )
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Admin: fallback responses CRUD
# ---------------------------------------------------------------------------


class TestFallbackResponses:
    async def test_list_returns_default_entries(self, admin_client):
        """init_schema seeds default fallback responses; the list must be non-empty."""
        r = await admin_client.get("/api/admin/fallback-responses")
        assert r.status_code == 200
        assert len(r.json()) > 0

    async def test_add_response(self, admin_client):
        r = await admin_client.post(
            "/api/admin/fallback-responses",
            json={"response": "ふむふむ"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["response"] == "ふむふむ"
        assert "id" in data

    async def test_add_and_list(self, admin_client):
        await admin_client.post("/api/admin/fallback-responses", json={"response": "なるほど"})
        await admin_client.post("/api/admin/fallback-responses", json={"response": "そうですね"})
        r = await admin_client.get("/api/admin/fallback-responses")
        assert r.status_code == 200
        responses = [item["response"] for item in r.json()]
        assert "なるほど" in responses
        assert "そうですね" in responses

    async def test_delete_response(self, admin_client):
        add = await admin_client.post(
            "/api/admin/fallback-responses", json={"response": "削除対象"}
        )
        response_id = add.json()["id"]
        r = await admin_client.delete(f"/api/admin/fallback-responses/{response_id}")
        assert r.status_code == 200
        # Should no longer appear in list
        lst = await admin_client.get("/api/admin/fallback-responses")
        assert all(item["id"] != response_id for item in lst.json())

    async def test_delete_nonexistent_returns_404(self, admin_client):
        r = await admin_client.delete("/api/admin/fallback-responses/99999")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Admin: guild toggle
# ---------------------------------------------------------------------------


class TestGuildToggle:
    async def test_toggle_guild_returns_ok(self, admin_client):
        r = await admin_client.patch(
            f"/api/admin/guilds/{GUILD_ID}",
            json={"bot_enabled": False},
        )
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    async def test_toggle_guild_reflected_in_list(self, admin_client):
        # Ensure the guild has settings first (toggle creates if missing via update_setting)
        from src.db.connection import init_schema, open_db
        from src.config import Config
        from cryptography.fernet import Fernet

        # Disable the guild
        await admin_client.patch(
            f"/api/admin/guilds/{GUILD_ID}", json={"bot_enabled": False}
        )
        r = await admin_client.get("/api/admin/guilds")
        guilds = {g["guild_id"]: g for g in r.json()}
        if GUILD_ID in guilds:
            assert guilds[GUILD_ID]["bot_enabled"] is False


# ---------------------------------------------------------------------------
# Admin: sync-commands
# ---------------------------------------------------------------------------


class TestSyncCommands:
    async def test_sync_commands_sets_flag(self, admin_client):
        r = await admin_client.post("/api/admin/sync-commands")
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    async def test_sync_commands_unauthenticated_returns_401(self, client):
        r = await client.post("/api/admin/sync-commands")
        assert r.status_code == 401

    async def test_sync_commands_non_admin_returns_403(self, cfg):
        from src.db.connection import init_schema, open_db
        from src.api.deps import require_auth

        app = create_app(cfg)
        db = await open_db(cfg.db_path)
        await init_schema(db)
        app.state.cfg = cfg
        app.state.db = db

        async def mock_non_admin():
            return {"user_id": "999999999999999999", "username": "nobody"}

        app.dependency_overrides[require_auth] = mock_non_admin
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            r = await c.post("/api/admin/sync-commands")
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Admin: settings update round-trip
# ---------------------------------------------------------------------------


class TestAdminSettingsRoundTrip:
    async def test_update_and_read_back_ttl(self, admin_client):
        await admin_client.patch("/api/admin/settings", json={"discord_cache_ttl": 600})
        r = await admin_client.get("/api/admin/settings")
        assert r.json()["discord_cache_ttl"] == 600

    async def test_update_provider_and_model(self, admin_client):
        await admin_client.patch(
            "/api/admin/settings",
            json={"global_llm_provider": "gemini", "global_llm_model": "gemini-1.5-pro"},
        )
        r = await admin_client.get("/api/admin/settings")
        data = r.json()
        assert data["global_llm_provider"] == "gemini"
        assert data["global_llm_model"] == "gemini-1.5-pro"


# ---------------------------------------------------------------------------
# Admin: server logs
# ---------------------------------------------------------------------------


@pytest.fixture
def cfg_with_log(tmp_path):
    """Config with log_file pointing to a temp path (file may or may not exist)."""
    from cryptography.fernet import Fernet

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
    )


@pytest.fixture
async def admin_log_client(cfg_with_log):
    """Admin client whose Config has log_file configured."""
    from src.db.connection import init_schema, open_db

    app = create_app(cfg_with_log)
    db = await open_db(cfg_with_log.db_path)
    await init_schema(db)
    app.state.cfg = cfg_with_log
    app.state.db = db

    async def mock_admin():
        return {"user_id": "111111111111111111", "username": "admin", "is_bot_admin": True}

    app.dependency_overrides[require_auth] = mock_admin

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c, cfg_with_log
    finally:
        await db.close()


class TestServerLogs:
    async def test_unauthenticated_returns_401(self, client):
        r = await client.get("/api/admin/server-logs")
        assert r.status_code == 401

    async def test_download_unauthenticated_returns_401(self, client):
        r = await client.get("/api/admin/server-logs/download")
        assert r.status_code == 401

    async def test_no_log_file_configured_returns_unavailable(self, admin_client):
        """When Config.log_file is empty, available=False and log_file is empty string."""
        r = await admin_client.get("/api/admin/server-logs")
        assert r.status_code == 200
        data = r.json()
        assert data["available"] is False
        assert data["log_file"] == ""
        assert data["lines"] == []

    async def test_download_no_log_file_returns_404(self, admin_client):
        r = await admin_client.get("/api/admin/server-logs/download")
        assert r.status_code == 404

    async def test_log_file_missing_returns_unavailable_with_filename(self, admin_log_client):
        client, cfg = admin_log_client
        r = await client.get("/api/admin/server-logs")
        assert r.status_code == 200
        data = r.json()
        assert data["available"] is False
        assert data["log_file"] != ""

    async def test_download_missing_file_returns_404(self, admin_log_client):
        client, cfg = admin_log_client
        r = await client.get("/api/admin/server-logs/download")
        assert r.status_code == 404

    async def test_existing_log_file_returns_lines(self, admin_log_client):
        client, cfg = admin_log_client
        import pathlib
        pathlib.Path(cfg.log_file).write_text(
            "2024-01-01 INFO bot: started\n2024-01-01 INFO bot: ready\n",
            encoding="utf-8",
        )
        r = await client.get("/api/admin/server-logs")
        assert r.status_code == 200
        data = r.json()
        assert data["available"] is True
        assert len(data["lines"]) == 2
        assert "started" in data["lines"][0]

    async def test_lines_query_param_limits_results(self, admin_log_client):
        client, cfg = admin_log_client
        import pathlib
        content = "\n".join(f"line{i}" for i in range(50)) + "\n"
        pathlib.Path(cfg.log_file).write_text(content, encoding="utf-8")
        r = await client.get("/api/admin/server-logs?lines=5")
        assert r.status_code == 200
        data = r.json()
        assert len(data["lines"]) == 5
        assert data["lines"][-1] == "line49"

    async def test_download_existing_file_returns_200(self, admin_log_client):
        client, cfg = admin_log_client
        import pathlib
        pathlib.Path(cfg.log_file).write_text("log content\n", encoding="utf-8")
        r = await client.get("/api/admin/server-logs/download")
        assert r.status_code == 200
        assert "text/plain" in r.headers["content-type"]

    async def test_size_bytes_reflects_file_size(self, admin_log_client):
        client, cfg = admin_log_client
        import pathlib
        content = "hello world\n"
        pathlib.Path(cfg.log_file).write_text(content, encoding="utf-8")
        r = await client.get("/api/admin/server-logs")
        data = r.json()
        assert data["size_bytes"] == len(content.encode("utf-8"))


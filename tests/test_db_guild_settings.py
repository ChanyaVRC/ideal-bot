from __future__ import annotations

import aiosqlite

from src.db import guild_settings as gs_db

GUILD = "g1"


async def test_ensure_settings_creates_default(db: aiosqlite.Connection):
    settings = await gs_db.ensure_settings(db, GUILD)
    assert settings.guild_id == GUILD
    assert settings.reply_rate == 10
    assert settings.bot_enabled is True


async def test_ensure_settings_idempotent(db: aiosqlite.Connection):
    await gs_db.ensure_settings(db, GUILD)
    settings = await gs_db.ensure_settings(db, GUILD)
    assert settings.reply_rate == 10


async def test_update_reply_rate(db: aiosqlite.Connection):
    await gs_db.update_setting(db, GUILD, reply_rate=50)
    settings = await gs_db.get_settings(db, GUILD)
    assert settings is not None
    assert settings.reply_rate == 50


async def test_update_bot_enabled_false(db: aiosqlite.Connection):
    await gs_db.update_setting(db, GUILD, bot_enabled=False)
    settings = await gs_db.get_settings(db, GUILD)
    assert settings is not None
    assert settings.bot_enabled is False


async def test_update_unknown_key_is_ignored(db: aiosqlite.Connection):
    # Should not raise; unknown keys are silently dropped
    await gs_db.update_setting(db, GUILD, nonexistent_field="value")
    settings = await gs_db.get_settings(db, GUILD)
    assert settings is not None


async def test_get_settings_returns_none_for_missing(db: aiosqlite.Connection):
    result = await gs_db.get_settings(db, "no_such_guild")
    assert result is None

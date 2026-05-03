from __future__ import annotations

import pytest
import aiosqlite

from src.db import bot_settings as bot_settings_db


async def test_get_missing_key_returns_none(db: aiosqlite.Connection):
    result = await bot_settings_db.get_value(db, "nonexistent_key")
    assert result is None


async def test_set_and_get_value(db: aiosqlite.Connection):
    await bot_settings_db.set_value(db, "my_key", "my_value")
    result = await bot_settings_db.get_value(db, "my_key")
    assert result == "my_value"


async def test_set_overwrites_existing_value(db: aiosqlite.Connection):
    await bot_settings_db.set_value(db, "k", "v1")
    await bot_settings_db.set_value(db, "k", "v2")
    assert await bot_settings_db.get_value(db, "k") == "v2"


async def test_delete_existing_key(db: aiosqlite.Connection):
    await bot_settings_db.set_value(db, "to_delete", "val")
    await bot_settings_db.delete_value(db, "to_delete")
    assert await bot_settings_db.get_value(db, "to_delete") is None


async def test_delete_nonexistent_key_is_noop(db: aiosqlite.Connection):
    await bot_settings_db.delete_value(db, "ghost_key")
    assert await bot_settings_db.get_value(db, "ghost_key") is None


async def test_multiple_keys_are_independent(db: aiosqlite.Connection):
    await bot_settings_db.set_value(db, "a", "1")
    await bot_settings_db.set_value(db, "b", "2")
    assert await bot_settings_db.get_value(db, "a") == "1"
    assert await bot_settings_db.get_value(db, "b") == "2"

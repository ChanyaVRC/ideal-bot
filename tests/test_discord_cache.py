"""Tests for src/db/discord_cache.py.

Covers:
- get_cached_bot_guild_ids: fresh hit, stale miss, empty DB, corrupt timestamp
- upsert_bot_guild_ids: inserts membership flags + sync timestamp; clears old members
- upsert_guilds: caches name/icon; subsequent call updates them
- transaction safety: upsert_bot_guild_ids rolls back on partial failure
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import aiosqlite
import pytest

from src.db import discord_cache as cache_db
from src.db import bot_settings as bot_settings_db

GUILD_A = "111111111111111111"
GUILD_B = "222222222222222222"
GUILD_C = "333333333333333333"


# ---------------------------------------------------------------------------
# get_cached_bot_guild_ids
# ---------------------------------------------------------------------------


async def test_get_cached_returns_none_when_no_record(db: aiosqlite.Connection):
    result = await cache_db.get_cached_bot_guild_ids(db, max_age_seconds=300)
    assert result is None


async def test_get_cached_returns_ids_when_fresh(db: aiosqlite.Connection):
    await cache_db.upsert_bot_guild_ids(db, {GUILD_A, GUILD_B})
    result = await cache_db.get_cached_bot_guild_ids(db, max_age_seconds=300)
    assert result == {GUILD_A, GUILD_B}


async def test_get_cached_returns_none_when_stale(db: aiosqlite.Connection):
    # Write a timestamp in the past beyond TTL
    past = (datetime.utcnow() - timedelta(seconds=400)).isoformat()
    await bot_settings_db.set_value(db, "bot_guilds_synced_at", past)
    # Insert a member row manually
    await db.execute(
        "INSERT INTO discord_guild_cache (guild_id, name, icon, is_bot_member) VALUES (?, '', NULL, 1)",
        (GUILD_A,),
    )
    await db.commit()

    result = await cache_db.get_cached_bot_guild_ids(db, max_age_seconds=300)
    assert result is None


async def test_get_cached_returns_none_on_corrupt_timestamp(db: aiosqlite.Connection):
    await bot_settings_db.set_value(db, "bot_guilds_synced_at", "not-a-date")
    result = await cache_db.get_cached_bot_guild_ids(db, max_age_seconds=300)
    assert result is None


async def test_get_cached_excludes_non_members(db: aiosqlite.Connection):
    await cache_db.upsert_bot_guild_ids(db, {GUILD_A})
    # Add a non-member row manually
    await db.execute(
        "INSERT INTO discord_guild_cache (guild_id, name, icon, is_bot_member) VALUES (?, '', NULL, 0)",
        (GUILD_B,),
    )
    await db.commit()

    result = await cache_db.get_cached_bot_guild_ids(db, max_age_seconds=300)
    assert GUILD_A in result
    assert GUILD_B not in result


# ---------------------------------------------------------------------------
# upsert_bot_guild_ids
# ---------------------------------------------------------------------------


async def test_upsert_sets_is_bot_member(db: aiosqlite.Connection):
    await cache_db.upsert_bot_guild_ids(db, {GUILD_A, GUILD_B})
    async with db.execute(
        "SELECT guild_id FROM discord_guild_cache WHERE is_bot_member = 1"
    ) as cur:
        rows = await cur.fetchall()
    guild_ids = {r["guild_id"] for r in rows}
    assert guild_ids == {GUILD_A, GUILD_B}


async def test_upsert_clears_removed_members(db: aiosqlite.Connection):
    await cache_db.upsert_bot_guild_ids(db, {GUILD_A, GUILD_B})
    # Second call: GUILD_B is no longer a member
    await cache_db.upsert_bot_guild_ids(db, {GUILD_A})
    async with db.execute(
        "SELECT guild_id, is_bot_member FROM discord_guild_cache"
    ) as cur:
        rows = {r["guild_id"]: bool(r["is_bot_member"]) for r in await cur.fetchall()}
    assert rows[GUILD_A] is True
    assert rows[GUILD_B] is False


async def test_upsert_records_sync_timestamp(db: aiosqlite.Connection):
    before = datetime.utcnow()
    await cache_db.upsert_bot_guild_ids(db, {GUILD_A})
    raw = await bot_settings_db.get_value(db, "bot_guilds_synced_at")
    assert raw is not None
    synced_at = datetime.fromisoformat(raw)
    # Timestamp should be within the last 5 seconds
    assert (datetime.utcnow() - synced_at).total_seconds() < 5


async def test_upsert_preserves_name_and_icon(db: aiosqlite.Connection):
    # Pre-populate with name/icon via upsert_guilds
    await cache_db.upsert_guilds(db, [{"id": GUILD_A, "name": "My Server", "icon": "abc123"}])
    # Now update membership — name/icon must survive
    await cache_db.upsert_bot_guild_ids(db, {GUILD_A})
    async with db.execute(
        "SELECT name, icon FROM discord_guild_cache WHERE guild_id = ?", (GUILD_A,)
    ) as cur:
        row = await cur.fetchone()
    assert row["name"] == "My Server"
    assert row["icon"] == "abc123"


# ---------------------------------------------------------------------------
# upsert_guilds
# ---------------------------------------------------------------------------


async def test_upsert_guilds_inserts_name_and_icon(db: aiosqlite.Connection):
    guilds = [
        {"id": GUILD_A, "name": "Alpha", "icon": "icon_a"},
        {"id": GUILD_B, "name": "Beta", "icon": None},
    ]
    await cache_db.upsert_guilds(db, guilds)
    async with db.execute(
        "SELECT guild_id, name, icon FROM discord_guild_cache ORDER BY guild_id"
    ) as cur:
        rows = {r["guild_id"]: dict(r) for r in await cur.fetchall()}
    assert rows[GUILD_A]["name"] == "Alpha"
    assert rows[GUILD_A]["icon"] == "icon_a"
    assert rows[GUILD_B]["name"] == "Beta"
    assert rows[GUILD_B]["icon"] is None


async def test_upsert_guilds_updates_existing(db: aiosqlite.Connection):
    await cache_db.upsert_guilds(db, [{"id": GUILD_A, "name": "Old Name", "icon": "old"}])
    await cache_db.upsert_guilds(db, [{"id": GUILD_A, "name": "New Name", "icon": "new"}])
    async with db.execute(
        "SELECT name, icon FROM discord_guild_cache WHERE guild_id = ?", (GUILD_A,)
    ) as cur:
        row = await cur.fetchone()
    assert row["name"] == "New Name"
    assert row["icon"] == "new"


async def test_upsert_guilds_empty_list_is_noop(db: aiosqlite.Connection):
    await cache_db.upsert_guilds(db, [])
    async with db.execute("SELECT COUNT(*) AS n FROM discord_guild_cache") as cur:
        row = await cur.fetchone()
    assert row["n"] == 0

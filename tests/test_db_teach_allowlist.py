from __future__ import annotations

import pytest
import aiosqlite

from src.db import teach_allowlist as allowlist_db

GUILD = "g1"


async def test_can_teach_when_allowlist_empty(db: aiosqlite.Connection):
    result = await allowlist_db.can_teach(db, GUILD, user_id=1, role_ids=[])
    assert result is True


async def test_can_teach_user_in_allowlist(db: aiosqlite.Connection):
    await allowlist_db.add_to_allowlist(db, GUILD, "42", "user")
    result = await allowlist_db.can_teach(db, GUILD, user_id=42, role_ids=[])
    assert result is True


async def test_cannot_teach_user_not_in_allowlist(db: aiosqlite.Connection):
    await allowlist_db.add_to_allowlist(db, GUILD, "100", "user")
    result = await allowlist_db.can_teach(db, GUILD, user_id=999, role_ids=[])
    assert result is False


async def test_can_teach_via_role(db: aiosqlite.Connection):
    await allowlist_db.add_to_allowlist(db, GUILD, "55", "role")
    result = await allowlist_db.can_teach(db, GUILD, user_id=999, role_ids=[55, 66])
    assert result is True


async def test_cannot_teach_wrong_role(db: aiosqlite.Connection):
    await allowlist_db.add_to_allowlist(db, GUILD, "55", "role")
    result = await allowlist_db.can_teach(db, GUILD, user_id=999, role_ids=[77])
    assert result is False


async def test_get_allowlist_returns_entries(db: aiosqlite.Connection):
    await allowlist_db.add_to_allowlist(db, GUILD, "1", "user")
    await allowlist_db.add_to_allowlist(db, GUILD, "2", "role")
    entries = await allowlist_db.get_allowlist(db, GUILD)
    assert len(entries) == 2
    target_ids = {e.target_id for e in entries}
    assert target_ids == {"1", "2"}


async def test_remove_from_allowlist_returns_true(db: aiosqlite.Connection):
    await allowlist_db.add_to_allowlist(db, GUILD, "1", "user")
    removed = await allowlist_db.remove_from_allowlist(db, GUILD, "1")
    assert removed is True
    entries = await allowlist_db.get_allowlist(db, GUILD)
    assert entries == []


async def test_remove_nonexistent_returns_false(db: aiosqlite.Connection):
    removed = await allowlist_db.remove_from_allowlist(db, GUILD, "999")
    assert removed is False


async def test_clear_allowlist(db: aiosqlite.Connection):
    await allowlist_db.add_to_allowlist(db, GUILD, "1", "user")
    await allowlist_db.add_to_allowlist(db, GUILD, "2", "role")
    await allowlist_db.clear_allowlist(db, GUILD)
    entries = await allowlist_db.get_allowlist(db, GUILD)
    assert entries == []


async def test_allowlist_is_guild_scoped(db: aiosqlite.Connection):
    await allowlist_db.add_to_allowlist(db, "guild_a", "1", "user")
    entries_a = await allowlist_db.get_allowlist(db, "guild_a")
    entries_b = await allowlist_db.get_allowlist(db, "guild_b")
    assert len(entries_a) == 1
    assert entries_b == []

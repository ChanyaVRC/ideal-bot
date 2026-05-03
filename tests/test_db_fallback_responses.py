from __future__ import annotations

import pytest
import aiosqlite

from src.db import fallback_responses as fallback_db

_SEED_COUNT = len(fallback_db.DEFAULT_FALLBACK_RESPONSES)


async def test_get_fallback_returns_seeded_defaults_on_init(db: aiosqlite.Connection):
    # Schema migration seeds defaults; they match DEFAULT_FALLBACK_RESPONSES
    result = await fallback_db.get_fallback_responses(db)
    assert result == fallback_db.DEFAULT_FALLBACK_RESPONSES


async def test_list_fallback_returns_seeded_rows(db: aiosqlite.Connection):
    result = await fallback_db.list_fallback_responses(db)
    assert len(result) == _SEED_COUNT


async def test_add_fallback_response_increases_count(db: aiosqlite.Connection):
    response_id = await fallback_db.add_fallback_response(db, "テストです")
    assert isinstance(response_id, int)
    rows = await fallback_db.list_fallback_responses(db)
    assert len(rows) == _SEED_COUNT + 1
    texts = [r[1] for r in rows]
    assert "テストです" in texts


async def test_add_auto_increments_sort_order(db: aiosqlite.Connection):
    id1 = await fallback_db.add_fallback_response(db, "first_extra")
    id2 = await fallback_db.add_fallback_response(db, "second_extra")
    rows = await fallback_db.list_fallback_responses(db)
    by_id = {r[0]: r[2] for r in rows}
    assert by_id[id1] < by_id[id2]


async def test_add_with_explicit_sort_order(db: aiosqlite.Connection):
    row_id = await fallback_db.add_fallback_response(db, "x", sort_order=5)
    rows = await fallback_db.list_fallback_responses(db)
    by_id = {r[0]: r[2] for r in rows}
    assert by_id[row_id] == 5


async def test_get_fallback_includes_custom_response(db: aiosqlite.Connection):
    await fallback_db.add_fallback_response(db, "カスタム応答")
    result = await fallback_db.get_fallback_responses(db)
    assert "カスタム応答" in result


async def test_delete_existing_response_returns_true(db: aiosqlite.Connection):
    response_id = await fallback_db.add_fallback_response(db, "delete me")
    deleted = await fallback_db.delete_fallback_response(db, response_id)
    assert deleted is True
    rows = await fallback_db.list_fallback_responses(db)
    texts = [r[1] for r in rows]
    assert "delete me" not in texts


async def test_delete_nonexistent_response_returns_false(db: aiosqlite.Connection):
    deleted = await fallback_db.delete_fallback_response(db, 99999)
    assert deleted is False


async def test_list_sort_order_respected(db: aiosqlite.Connection):
    await fallback_db.add_fallback_response(db, "high_order", sort_order=200)
    await fallback_db.add_fallback_response(db, "low_order", sort_order=1)
    rows = await fallback_db.list_fallback_responses(db)
    orders = [r[2] for r in rows]
    assert orders == sorted(orders)

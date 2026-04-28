from __future__ import annotations

import pytest
import aiosqlite

from src.db.connection import init_schema


@pytest.fixture
async def db() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await init_schema(conn)
    yield conn
    await conn.close()

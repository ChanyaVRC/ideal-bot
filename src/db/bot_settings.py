from __future__ import annotations

import aiosqlite


async def get_value(db: aiosqlite.Connection, key: str) -> str | None:
    async with db.execute(
        "SELECT value FROM bot_settings WHERE key = ?", (key,)
    ) as cursor:
        row = await cursor.fetchone()
    return row["value"] if row else None


async def set_value(db: aiosqlite.Connection, key: str, value: str) -> None:
    await db.execute(
        "INSERT INTO bot_settings (key, value) VALUES (?, ?)"
        " ON CONFLICT (key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    await db.commit()


async def delete_value(db: aiosqlite.Connection, key: str) -> None:
    await db.execute("DELETE FROM bot_settings WHERE key = ?", (key,))
    await db.commit()

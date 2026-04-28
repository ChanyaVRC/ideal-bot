from __future__ import annotations

from datetime import datetime

import aiosqlite

_BOT_GUILDS_SYNCED_AT_KEY = "bot_guilds_synced_at"


async def get_cached_bot_guild_ids(
    db: aiosqlite.Connection, max_age_seconds: int
) -> set[str] | None:
    """Return cached bot guild ID set if still fresh, else None."""
    async with db.execute(
        "SELECT value FROM bot_settings WHERE key = ?",
        (_BOT_GUILDS_SYNCED_AT_KEY,),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return None

    try:
        synced_at = datetime.fromisoformat(row["value"])
    except ValueError:
        return None
    age = (datetime.utcnow() - synced_at).total_seconds()
    if age > max_age_seconds:
        return None

    async with db.execute(
        "SELECT guild_id FROM discord_guild_cache WHERE is_bot_member = 1"
    ) as cursor:
        rows = await cursor.fetchall()
    return {r["guild_id"] for r in rows}


async def upsert_bot_guild_ids(
    db: aiosqlite.Connection, guild_ids: set[str]
) -> None:
    """Overwrite bot membership flags and record sync timestamp."""
    # Run all writes in a single transaction so a mid-flight failure leaves
    # the table in its previous state rather than a partially-updated one.
    try:
        await db.execute("UPDATE discord_guild_cache SET is_bot_member = 0")
        for guild_id in guild_ids:
            await db.execute(
                """
                INSERT INTO discord_guild_cache (guild_id, name, icon, is_bot_member, cached_at)
                VALUES (?, '', NULL, 1, datetime('now'))
                ON CONFLICT (guild_id) DO UPDATE SET
                    is_bot_member = 1,
                    cached_at     = datetime('now')
                """,
                (guild_id,),
            )
        await db.execute(
            "INSERT INTO bot_settings (key, value) VALUES (?, datetime('now'))"
            " ON CONFLICT (key) DO UPDATE SET value = datetime('now')",
            (_BOT_GUILDS_SYNCED_AT_KEY,),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def upsert_guilds(
    db: aiosqlite.Connection,
    guilds: list[dict],
) -> None:
    """Cache / refresh name and icon for each guild in the list."""
    for g in guilds:
        await db.execute(
            """
            INSERT INTO discord_guild_cache (guild_id, name, icon, cached_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT (guild_id) DO UPDATE SET
                name      = excluded.name,
                icon      = excluded.icon,
                cached_at = excluded.cached_at
            """,
            (g["id"], g.get("name", ""), g.get("icon")),
        )
    await db.commit()

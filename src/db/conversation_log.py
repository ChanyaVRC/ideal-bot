from __future__ import annotations

from dataclasses import dataclass

import aiosqlite


@dataclass
class LogMessage:
    id: int
    guild_id: str
    channel_id: str
    author_id: str
    content: str
    is_bot: bool
    reply_context: str | None
    generation_metadata: str | None
    created_at: str


async def add_message(
    db: aiosqlite.Connection,
    guild_id: str,
    channel_id: str,
    author_id: str,
    content: str,
    is_bot: bool,
    reply_context: str | None = None,
    generation_metadata: str | None = None,
) -> None:
    await db.execute(
        """
        INSERT INTO conversation_log (
            guild_id,
            channel_id,
            author_id,
            content,
            is_bot,
            reply_context,
            generation_metadata
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (guild_id, channel_id, author_id, content, int(is_bot), reply_context, generation_metadata),
    )
    await db.commit()


async def get_recent_messages(
    db: aiosqlite.Connection,
    guild_id: str,
    channel_id: str,
    limit: int = 10,
) -> list[LogMessage]:
    async with db.execute(
        """
        SELECT * FROM (
            SELECT * FROM conversation_log
            WHERE guild_id = ? AND channel_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ) ORDER BY created_at ASC
        """,
        (guild_id, channel_id, limit),
    ) as cursor:
        rows = await cursor.fetchall()
    return [
        LogMessage(
            id=row["id"],
            guild_id=row["guild_id"],
            channel_id=row["channel_id"],
            author_id=row["author_id"],
            content=row["content"],
            is_bot=bool(row["is_bot"]),
            reply_context=row["reply_context"],
            generation_metadata=row["generation_metadata"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


async def purge_channel(
    db: aiosqlite.Connection,
    guild_id: str,
    channel_id: str,
    max_count: int = 20,
) -> None:
    """Keep only the most recent max_count messages per channel."""
    await db.execute(
        """
        DELETE FROM conversation_log
        WHERE guild_id = ? AND channel_id = ? AND id NOT IN (
            SELECT id FROM conversation_log
            WHERE guild_id = ? AND channel_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        )
        """,
        (guild_id, channel_id, guild_id, channel_id, max_count),
    )
    await db.commit()


async def purge_old_messages(
    db: aiosqlite.Connection, retention_days: int
) -> None:
    await db.execute(
        """
        DELETE FROM conversation_log
        WHERE created_at < datetime('now', ? || ' days')
        """,
        (f"-{retention_days}",),
    )
    await db.commit()


async def list_messages(
    db: aiosqlite.Connection,
    *,
    limit: int = 100,
    offset: int = 0,
    guild_id: str | None = None,
) -> list[LogMessage]:
    if guild_id:
        query = """
            SELECT * FROM conversation_log
            WHERE guild_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
        """
        params = (guild_id, limit, offset)
    else:
        query = """
            SELECT * FROM conversation_log
            ORDER BY created_at DESC, id DESC
            LIMIT ? OFFSET ?
        """
        params = (limit, offset)

    async with db.execute(query, params) as cursor:
        rows = await cursor.fetchall()
    return [
        LogMessage(
            id=row["id"],
            guild_id=row["guild_id"],
            channel_id=row["channel_id"],
            author_id=row["author_id"],
            content=row["content"],
            is_bot=bool(row["is_bot"]),
            reply_context=row["reply_context"],
            generation_metadata=row["generation_metadata"],
            created_at=row["created_at"],
        )
        for row in rows
    ]

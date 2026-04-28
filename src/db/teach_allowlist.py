from __future__ import annotations

from dataclasses import dataclass

import aiosqlite


@dataclass
class AllowlistEntry:
    id: int
    guild_id: str
    target_id: str
    target_type: str  # 'role' | 'user'


async def get_allowlist(
    db: aiosqlite.Connection, guild_id: str
) -> list[AllowlistEntry]:
    async with db.execute(
        "SELECT * FROM teach_allowlist WHERE guild_id = ?",
        (guild_id,),
    ) as cursor:
        rows = await cursor.fetchall()
    return [AllowlistEntry(**dict(row)) for row in rows]


async def add_to_allowlist(
    db: aiosqlite.Connection,
    guild_id: str,
    target_id: str,
    target_type: str,
) -> None:
    await db.execute(
        """
        INSERT OR IGNORE INTO teach_allowlist (guild_id, target_id, target_type)
        VALUES (?, ?, ?)
        """,
        (guild_id, target_id, target_type),
    )
    await db.commit()


async def remove_from_allowlist(
    db: aiosqlite.Connection, guild_id: str, target_id: str
) -> bool:
    cursor = await db.execute(
        "DELETE FROM teach_allowlist WHERE guild_id = ? AND target_id = ?",
        (guild_id, target_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def clear_allowlist(db: aiosqlite.Connection, guild_id: str) -> None:
    await db.execute("DELETE FROM teach_allowlist WHERE guild_id = ?", (guild_id,))
    await db.commit()


async def can_teach(
    db: aiosqlite.Connection,
    guild_id: str,
    user_id: int,
    role_ids: list[int],
) -> bool:
    entries = await get_allowlist(db, guild_id)
    if not entries:
        return True
    allowed = {e.target_id for e in entries}
    if str(user_id) in allowed:
        return True
    return any(str(rid) in allowed for rid in role_ids)

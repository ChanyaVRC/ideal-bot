from __future__ import annotations

from dataclasses import dataclass

import aiosqlite


@dataclass
class GuildSettings:
    guild_id: str
    reply_rate: int = 10
    bot_enabled: bool = True
    llm_api_key: str | None = None
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    bot_persona: str | None = None
    context_count: int = 10
    conversation_ttl: int = 5
    delay_read_min: float | None = None
    delay_read_max: float | None = None
    delay_type_cps: float | None = None


def _row_to_settings(row: aiosqlite.Row) -> GuildSettings:
    d = dict(row)
    d["bot_enabled"] = bool(d.get("bot_enabled", True))
    return GuildSettings(**{k: v for k, v in d.items() if k in GuildSettings.__dataclass_fields__})


async def get_settings(
    db: aiosqlite.Connection, guild_id: str
) -> GuildSettings | None:
    async with db.execute(
        "SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)
    ) as cursor:
        row = await cursor.fetchone()
    return _row_to_settings(row) if row else None


async def ensure_settings(
    db: aiosqlite.Connection, guild_id: str
) -> GuildSettings:
    settings = await get_settings(db, guild_id)
    if settings is not None:
        return settings
    await db.execute(
        "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
    )
    await db.commit()
    return GuildSettings(guild_id=guild_id)


async def update_setting(
    db: aiosqlite.Connection, guild_id: str, **kwargs: object
) -> None:
    await ensure_settings(db, guild_id)
    allowed = {f for f in GuildSettings.__dataclass_fields__ if f != "guild_id"}
    filtered = {k: v for k, v in kwargs.items() if k in allowed}
    if not filtered:
        return
    sets = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [guild_id]
    await db.execute(
        f"UPDATE guild_settings SET {sets} WHERE guild_id = ?", values
    )
    await db.commit()

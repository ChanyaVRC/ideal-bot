from __future__ import annotations

from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from src.config import Config
from src.db import guild_settings as gs_db
from src.db import words as words_db
from src.utils.encryption import encrypt
from src.api.deps import get_cfg, get_db, guild_access
from src.api.models import (
    GuildSettingsResponse,
    GuildSettingsUpdate,
    WordResponse,
)

router = APIRouter()


@router.get("/{guild_id}/settings", response_model=GuildSettingsResponse)
async def get_settings(
    guild_id: str,
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
    _user: Annotated[dict, Depends(guild_access)],
):
    s = await gs_db.ensure_settings(db, guild_id)
    return GuildSettingsResponse(
        guild_id=s.guild_id,
        reply_rate=s.reply_rate,
        bot_enabled=s.bot_enabled,
        llm_provider=s.llm_provider,
        llm_model=s.llm_model,
        bot_persona=s.bot_persona,
        context_count=s.context_count,
        conversation_ttl=s.conversation_ttl,
        delay_read_min=s.delay_read_min,
        delay_read_max=s.delay_read_max,
        delay_type_cps=s.delay_type_cps,
        has_api_key=bool(s.llm_api_key),
    )


@router.patch("/{guild_id}/settings")
async def update_settings(
    guild_id: str,
    body: GuildSettingsUpdate,
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
    cfg: Annotated[Config, Depends(get_cfg)],
    _user: Annotated[dict, Depends(guild_access)],
):
    updates = body.model_dump(exclude_none=True, exclude={"llm_api_key"})
    if body.llm_api_key is not None:
        if body.llm_api_key == "":
            updates["llm_api_key"] = None
        else:
            updates["llm_api_key"] = encrypt(cfg.encryption_master_key, body.llm_api_key)
    if updates:
        await gs_db.update_setting(db, guild_id, **updates)
    return {"ok": True}


@router.get("/{guild_id}/words", response_model=list[WordResponse])
async def list_words(
    guild_id: str,
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
    _user: Annotated[dict, Depends(guild_access)],
):
    words = await words_db.get_words(db, guild_id)
    return [
        WordResponse(
            word=w.word,
            reading=w.reading,
            category=w.category,
            category_reading=w.category_reading,
            added_by=w.added_by,
            created_at=w.created_at,
        )
        for w in words
    ]


@router.delete("/{guild_id}/words/{reading}")
async def delete_word(
    guild_id: str,
    reading: str,
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
    _user: Annotated[dict, Depends(guild_access)],
):
    word = await words_db.get_word_by_reading(db, guild_id, reading)
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    await words_db.delete_word_by_reading(db, guild_id, reading)
    return {"ok": True}

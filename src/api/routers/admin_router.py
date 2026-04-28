from __future__ import annotations

from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query

from src.config import Config
from src.db import bot_settings as bot_settings_db
from src.db import conversation_log as log_db
from src.db import fallback_responses as fallback_db
from src.db import guild_settings as gs_db
from src.utils.encryption import encrypt
from src.api.deps import get_cfg, get_db, require_bot_admin
from src.api.models import (
    AdminSettingsResponse,
    AdminSettingsUpdate,
    ConversationLogEntry,
    FallbackResponse,
    FallbackResponseCreate,
    GuildAdminInfo,
    GuildToggle,
)
from src.ai.local import DEFAULT_LOCAL_SYSTEM_PROMPT

router = APIRouter(dependencies=[Depends(require_bot_admin)])


@router.get("/settings", response_model=AdminSettingsResponse)
async def get_settings(
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
    cfg: Annotated[Config, Depends(get_cfg)],
):
    has_key = bool(await bot_settings_db.get_value(db, "global_llm_api_key"))
    provider = await bot_settings_db.get_value(db, "global_llm_provider") or "openai"
    model = await bot_settings_db.get_value(db, "global_llm_model") or "gpt-4o-mini"
    ttl_str = await bot_settings_db.get_value(db, "discord_cache_ttl")
    local_sys = await bot_settings_db.get_value(db, "local_system_prompt") or DEFAULT_LOCAL_SYSTEM_PROMPT
    local_dtype = await bot_settings_db.get_value(db, "local_torch_dtype") or "auto"
    local_quant = await bot_settings_db.get_value(db, "local_quantization_mode") or "4bit"
    return AdminSettingsResponse(
        has_global_api_key=has_key,
        global_llm_provider=provider,
        global_llm_model=model,
        discord_cache_ttl=int(ttl_str) if ttl_str else 300,
        local_system_prompt=local_sys,
        local_torch_dtype=local_dtype,
        local_quantization_mode=local_quant,
    )


@router.patch("/settings")
async def update_settings(
    body: AdminSettingsUpdate,
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
    cfg: Annotated[Config, Depends(get_cfg)],
):
    if body.global_llm_api_key is not None:
        if body.global_llm_api_key == "":
            await bot_settings_db.delete_value(db, "global_llm_api_key")
        else:
            await bot_settings_db.set_value(
                db,
                "global_llm_api_key",
                encrypt(cfg.encryption_master_key, body.global_llm_api_key),
            )
    if body.global_llm_provider is not None:
        await bot_settings_db.set_value(db, "global_llm_provider", body.global_llm_provider)
    if body.global_llm_model is not None:
        await bot_settings_db.set_value(db, "global_llm_model", body.global_llm_model)
    if body.discord_cache_ttl is not None:
        await bot_settings_db.set_value(db, "discord_cache_ttl", str(body.discord_cache_ttl))
    if body.local_system_prompt is not None:
        await bot_settings_db.set_value(db, "local_system_prompt", body.local_system_prompt)
    _VALID_DTYPES = {"auto", "bfloat16", "float16", "float32"}
    _VALID_QUANT = {"none", "4bit", "8bit"}
    if body.local_torch_dtype is not None:
        if body.local_torch_dtype not in _VALID_DTYPES:
            raise HTTPException(status_code=422, detail=f"local_torch_dtype must be one of {sorted(_VALID_DTYPES)}")
        await bot_settings_db.set_value(db, "local_torch_dtype", body.local_torch_dtype)
    if body.local_quantization_mode is not None:
        if body.local_quantization_mode not in _VALID_QUANT:
            raise HTTPException(status_code=422, detail=f"local_quantization_mode must be one of {sorted(_VALID_QUANT)}")
        await bot_settings_db.set_value(db, "local_quantization_mode", body.local_quantization_mode)
    return {"ok": True}


@router.get("/guilds", response_model=list[GuildAdminInfo])
async def list_guilds(db: Annotated[aiosqlite.Connection, Depends(get_db)]):
    async with db.execute(
        """
        SELECT gs.guild_id, gs.bot_enabled,
               dc.name AS name, dc.icon AS icon
        FROM guild_settings gs
        LEFT JOIN discord_guild_cache dc ON dc.guild_id = gs.guild_id
        ORDER BY gs.guild_id
        """
    ) as cursor:
        rows = await cursor.fetchall()
    return [
        GuildAdminInfo(
            guild_id=row["guild_id"],
            bot_enabled=bool(row["bot_enabled"]),
            name=row["name"] or None,
            icon=row["icon"],
        )
        for row in rows
    ]


@router.patch("/guilds/{guild_id}")
async def toggle_guild(
    guild_id: str,
    body: GuildToggle,
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
):
    await gs_db.update_setting(db, guild_id, bot_enabled=body.bot_enabled)
    return {"ok": True}


@router.get("/logs", response_model=list[ConversationLogEntry])
async def list_conversation_logs(
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    guild_id: str | None = Query(default=None),
):
    logs = await log_db.list_messages(
        db,
        limit=limit,
        offset=offset,
        guild_id=guild_id,
    )
    return [ConversationLogEntry(**log.__dict__) for log in logs]


@router.get("/fallback-responses", response_model=list[FallbackResponse])
async def list_fallback_responses(db: Annotated[aiosqlite.Connection, Depends(get_db)]):
    rows = await fallback_db.list_fallback_responses(db)
    return [
        FallbackResponse(
            id=row[0],
            response=row[1],
            sort_order=row[2],
            created_at=row[3],
        )
        for row in rows
    ]


@router.post("/fallback-responses", response_model=FallbackResponse)
async def add_fallback_response(
    body: FallbackResponseCreate,
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
):
    response_id = await fallback_db.add_fallback_response(db, body.response)
    async with db.execute(
        "SELECT id, response, sort_order, created_at FROM fallback_responses WHERE id = ?",
        (response_id,),
    ) as cursor:
        row = await cursor.fetchone()
    return FallbackResponse(
        id=row["id"],
        response=row["response"],
        sort_order=row["sort_order"],
        created_at=row["created_at"],
    )


@router.delete("/fallback-responses/{response_id}")
async def delete_fallback_response(
    response_id: int,
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
):
    deleted = await fallback_db.delete_fallback_response(db, response_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Fallback response not found")
    return {"ok": True}


@router.post("/sync-commands")
async def request_sync_commands(db: Annotated[aiosqlite.Connection, Depends(get_db)]):
    """Set a flag in bot_settings that the bot polls to trigger tree.sync()."""
    await bot_settings_db.set_value(db, "sync_commands_requested", "1")
    return {"ok": True}


@router.post("/reload-generator")
async def request_reload_generator(db: Annotated[aiosqlite.Connection, Depends(get_db)]):
    """Set a flag in bot_settings that the bot polls to trigger generator reload."""
    await bot_settings_db.set_value(db, "reload_generator_requested", "1")
    return {"ok": True}

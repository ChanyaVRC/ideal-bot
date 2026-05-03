from __future__ import annotations

import asyncio
import os
from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

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
    ServerLogResponse,
)
from src.ai.local import DEFAULT_LOCAL_SYSTEM_PROMPT

router = APIRouter(dependencies=[Depends(require_bot_admin)])

_KNOWN_DTYPES = [
    "auto",
    "bfloat16",
    "float16",
    "float32",
    "float64",
    "float8_e4m3fn",
    "float8_e5m2",
    "float8_e4m3fnuz",
    "float8_e5m2fnuz",
    "float8_e8m0fnu",
    "float4_e2m1fn_x2",
]

# Dtypes that transformers' from_pretrained actually accepts as torch_dtype for
# standard model loading. float8/float4 variants exist in newer torch builds but
# are not supported by transformers as a torch_dtype argument.
_TRANSFORMERS_USABLE_DTYPES: frozenset[str] = frozenset({
    "auto", "float16", "bfloat16", "float32", "float64",
})


def _get_supported_torch_dtypes() -> list[str]:
    supported = ["auto"]
    try:
        import torch
    except Exception:
        return supported

    for dtype_name in _KNOWN_DTYPES:
        if dtype_name == "auto":
            continue
        if dtype_name not in _TRANSFORMERS_USABLE_DTYPES:
            continue
        if getattr(torch, dtype_name, None) is not None:
            supported.append(dtype_name)
    return supported


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
    supported_dtypes = _get_supported_torch_dtypes()
    local_quant = await bot_settings_db.get_value(db, "local_quantization_mode") or "4bit"
    vllm_base_url = await bot_settings_db.get_value(db, "vllm_base_url") or ""
    return AdminSettingsResponse(
        has_global_api_key=has_key,
        global_llm_provider=provider,
        global_llm_model=model,
        discord_cache_ttl=int(ttl_str) if ttl_str else 300,
        cpu_only_mode=cfg.cpu_only_mode,
        local_system_prompt=local_sys,
        local_torch_dtype=local_dtype,
        local_supported_torch_dtypes=supported_dtypes,
        local_quantization_mode=local_quant,
        vllm_base_url=vllm_base_url,
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
    _VALID_DTYPES = set(_KNOWN_DTYPES)
    _SUPPORTED_DTYPES = set(_get_supported_torch_dtypes())
    _VALID_QUANT = {"none", "4bit", "8bit"}
    if body.local_torch_dtype is not None:
        if body.local_torch_dtype not in _VALID_DTYPES:
            raise HTTPException(status_code=422, detail=f"local_torch_dtype must be one of {sorted(_VALID_DTYPES)}")
        if body.local_torch_dtype not in _SUPPORTED_DTYPES:
            raise HTTPException(
                status_code=422,
                detail=(
                    "local_torch_dtype is not supported in this runtime. "
                    f"supported: {sorted(_SUPPORTED_DTYPES)}"
                ),
            )
        await bot_settings_db.set_value(db, "local_torch_dtype", body.local_torch_dtype)
    if body.local_quantization_mode is not None:
        if body.local_quantization_mode not in _VALID_QUANT:
            raise HTTPException(status_code=422, detail=f"local_quantization_mode must be one of {sorted(_VALID_QUANT)}")
        await bot_settings_db.set_value(db, "local_quantization_mode", body.local_quantization_mode)
    if body.vllm_base_url is not None:
        if body.vllm_base_url == "":
            await bot_settings_db.delete_value(db, "vllm_base_url")
        else:
            await bot_settings_db.set_value(db, "vllm_base_url", body.vllm_base_url)
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


_TAIL_MAX_BYTES = 50 * 1024 * 1024  # 50 MB — safety cap against enormous log files
_DOWNLOAD_MAX_BYTES = 500 * 1024 * 1024  # 500 MB


def _tail_lines(path: str, n: int) -> list[str]:
    """Read the last n lines from a file efficiently without loading the whole file.

    Reads at most _TAIL_MAX_BYTES from the end of the file so that requesting
    a large number of lines on a huge log does not exhaust server memory.
    """
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size == 0:
                return []
            buf = bytearray()
            chunk = 8192
            lines_found = 0
            bytes_read = 0
            pos = size
            while pos > 0 and lines_found < n + 1 and bytes_read < _TAIL_MAX_BYTES:
                read_size = min(chunk, pos, _TAIL_MAX_BYTES - bytes_read)
                pos -= read_size
                f.seek(pos)
                data = f.read(read_size)
                buf = bytearray(data) + buf
                lines_found = buf.count(b"\n")
                bytes_read += read_size
            text = buf.decode("utf-8", errors="replace")
            return text.splitlines()[-n:]
    except (FileNotFoundError, PermissionError, OSError):
        return []


def _resolve_log_path(log_file: str) -> "Path":
    """Resolve and validate the log file path to prevent path traversal."""
    from pathlib import Path
    return Path(log_file).resolve()


@router.get("/server-logs", response_model=ServerLogResponse)
async def get_server_logs(
    cfg: Annotated[Config, Depends(get_cfg)],
    lines: int = Query(default=200, ge=1, le=5000),
):
    if not cfg.log_file:
        return ServerLogResponse(lines=[], log_file="", available=False)

    log_path = _resolve_log_path(cfg.log_file)
    try:
        size = log_path.stat().st_size
    except (FileNotFoundError, PermissionError, OSError):
        return ServerLogResponse(lines=[], log_file=cfg.log_file, available=False)

    recent = await asyncio.get_running_loop().run_in_executor(
        None, _tail_lines, str(log_path), lines
    )
    return ServerLogResponse(
        lines=recent,
        log_file=log_path.name,
        available=True,
        size_bytes=size,
    )


@router.get("/server-logs/download")
async def download_server_logs(cfg: Annotated[Config, Depends(get_cfg)]):
    if not cfg.log_file:
        raise HTTPException(status_code=404, detail="log_file is not configured")
    log_path = _resolve_log_path(cfg.log_file)
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    size = log_path.stat().st_size
    if size > _DOWNLOAD_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Log file is too large to download directly "
                f"({size / (1024 * 1024):.1f} MB, limit {_DOWNLOAD_MAX_BYTES // (1024 * 1024)} MB). "
                "Rotate or truncate the log file first."
            ),
        )
    return FileResponse(
        str(log_path),
        media_type="text/plain; charset=utf-8",
        filename=log_path.name,
    )

from __future__ import annotations

import logging
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from src.api.auth import (
    exchange_code,
    filter_bot_joined_guilds,
    filter_managed_guilds,
    get_bot_guild_ids,
    get_bot_user,
    get_discord_guilds,
    get_discord_user,
    oauth_redirect_url,
)
from src.api.deps import get_cfg, require_auth
from src.api.models import BotInfo, ManagedGuild, UserInfo
from src.db import bot_settings as bot_settings_db
from src.db import discord_cache as discord_cache_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/login")
async def login(request: Request, cfg=Depends(get_cfg)):
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    logger.info("OAuth login started: client=%s", request.client.host if request.client else "unknown")
    return RedirectResponse(url=oauth_redirect_url(cfg, state))


@router.get("/bot", response_model=BotInfo)
async def bot_info(request: Request, cfg=Depends(get_cfg)):
    try:
        bot = await get_bot_user(cfg.discord_token, http_client=request.app.state.http_client)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Discord API error") from exc
    return BotInfo(name=bot.get("username", "Bot"), avatar=bot.get("avatar"))


@router.get("/callback")
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    cfg=Depends(get_cfg),
):
    if error:
        logger.info("OAuth callback error: error=%s", error)
        base = str(request.base_url).rstrip("/")
        return RedirectResponse(url=f"{base}/login?error={error}")
    if not code or not state:
        logger.info("OAuth callback rejected: missing code/state")
        raise HTTPException(status_code=400, detail="Missing code or state")
    if state != request.session.pop("oauth_state", None):
        logger.info("OAuth callback rejected: invalid state")
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    http_client = request.app.state.http_client
    try:
        token_data = await exchange_code(cfg, code, http_client=http_client)
        access_token = token_data["access_token"]
        discord_user = await get_discord_user(access_token, http_client=http_client)
        all_guilds = await get_discord_guilds(access_token, http_client=http_client)
        bot_user = await get_bot_user(cfg.discord_token, http_client=http_client)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Discord API error") from exc

    managed = filter_managed_guilds(all_guilds)
    request.session["user"] = {
        "user_id": discord_user["id"],
        "username": discord_user.get("global_name") or discord_user["username"],
        "avatar": discord_user.get("avatar"),
    }
    request.session["managed_guilds"] = [g["id"] for g in managed]
    # Store access token to re-fetch guild info on demand (avoids cookie size limit)
    request.session["discord_access_token"] = access_token
    # Warm the in-memory guild cache so the first /guilds call is instant
    request.app.state.guild_cache[discord_user["id"]] = {
        "guilds": all_guilds,
        "fetched_at": datetime.utcnow(),
    }
    request.session["bot_name"] = bot_user.get("username")
    request.session["bot_avatar"] = bot_user.get("avatar")
    logger.info(
        "OAuth login success: user_id=%s is_bot_admin=%s managed_guilds=%d",
        discord_user["id"],
        discord_user["id"] in cfg.bot_admin_ids,
        len(managed),
    )

    # Redirect to the origin of the API server (same as frontend in production).
    # This avoids relying on cfg.frontend_url which may point to the Vite dev server.
    base = str(request.base_url).rstrip("/")
    guild_id = request.query_params.get("guild")
    if guild_id:
        return RedirectResponse(url=f"{base}/guild/{guild_id}")
    return RedirectResponse(url=f"{base}/guilds")


@router.post("/logout")
async def logout(request: Request):
    user = request.session.get("user") or {}
    user_id = user.get("user_id")
    logger.info("Logout: user_id=%s", user_id or "anonymous")
    if user_id:
        request.app.state.guild_cache.pop(user_id, None)
    request.session.clear()
    return {"ok": True}


@router.get("/me", response_model=UserInfo)
async def me(request: Request, user: dict = Depends(require_auth)):
    cfg = request.app.state.cfg
    return UserInfo(
        user_id=user["user_id"],
        username=user["username"],
        avatar=user.get("avatar"),
        managed_guilds=request.session.get("managed_guilds", []),
        is_bot_admin=user["user_id"] in cfg.bot_admin_ids,
        bot_name=request.session.get("bot_name"),
        bot_avatar=request.session.get("bot_avatar"),
    )


@router.get("/guilds", response_model=list[ManagedGuild])
async def managed_guilds(request: Request, _user: dict = Depends(require_auth)):
    access_token = request.session.get("discord_access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="No Discord token in session")
    cfg = request.app.state.cfg
    db = request.app.state.db

    ttl_str = await bot_settings_db.get_value(db, "discord_cache_ttl")
    ttl = int(ttl_str) if ttl_str else 300

    http_client = request.app.state.http_client
    user_id = _user["user_id"]

    # Try to use cached bot guild IDs; fall back to Discord API on miss/expiry
    bot_guild_ids = await discord_cache_db.get_cached_bot_guild_ids(db, ttl)
    if bot_guild_ids is None:
        try:
            bot_guild_ids = await get_bot_guild_ids(cfg.discord_token, http_client=http_client)
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Discord API error") from exc
        await discord_cache_db.upsert_bot_guild_ids(db, bot_guild_ids)

    # Use in-memory cache for user guild list (avoids per-request Discord API call)
    cached = request.app.state.guild_cache.get(user_id)
    if cached and (datetime.utcnow() - cached["fetched_at"]).total_seconds() < ttl:
        all_guilds = cached["guilds"]
    else:
        try:
            all_guilds = await get_discord_guilds(access_token, http_client=http_client)
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Discord API error") from exc
        request.app.state.guild_cache[user_id] = {
            "guilds": all_guilds,
            "fetched_at": datetime.utcnow(),
        }

    filtered = filter_bot_joined_guilds(all_guilds, bot_guild_ids)

    # Cache guild name/icon for admin use
    await discord_cache_db.upsert_guilds(db, filtered)

    return [ManagedGuild(**g) for g in filtered]

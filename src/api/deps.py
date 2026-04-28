from __future__ import annotations

from typing import Annotated

import aiosqlite
from fastapi import Depends, HTTPException, Request

from src.config import Config


def get_db(request: Request) -> aiosqlite.Connection:
    return request.app.state.db


def get_cfg(request: Request) -> Config:
    return request.app.state.cfg


def require_auth(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_bot_admin(
    request: Request,
    user: Annotated[dict, Depends(require_auth)],
) -> dict:
    cfg: Config = request.app.state.cfg
    if user["user_id"] not in cfg.bot_admin_ids:
        raise HTTPException(status_code=403, detail="Bot admin only")
    return user


def guild_access(
    guild_id: str,
    request: Request,
    user: Annotated[dict, Depends(require_auth)],
) -> dict:
    cfg: Config = request.app.state.cfg
    managed = request.session.get("managed_guilds", [])
    if guild_id not in managed and user["user_id"] not in cfg.bot_admin_ids:
        raise HTTPException(status_code=403, detail="No access to this guild")
    return user

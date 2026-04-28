from __future__ import annotations

from urllib.parse import urlencode

import httpx

from src.config import Config

DISCORD_API = "https://discord.com/api/v10"
DISCORD_OAUTH_AUTHORIZE = "https://discord.com/oauth2/authorize"
MANAGE_GUILD = 0x20


def oauth_redirect_url(cfg: Config, state: str) -> str:
    params = {
        "client_id": cfg.discord_client_id,
        "redirect_uri": cfg.discord_redirect_uri,
        "response_type": "code",
        "scope": "identify guilds",
        "state": state,
    }
    return f"{DISCORD_OAUTH_AUTHORIZE}?{urlencode(params)}"


async def exchange_code(cfg: Config, code: str, *, http_client: httpx.AsyncClient) -> dict:
    r = await http_client.post(
        f"{DISCORD_API}/oauth2/token",
        data={
            "client_id": cfg.discord_client_id,
            "client_secret": cfg.discord_client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": cfg.discord_redirect_uri,
        },
    )
    r.raise_for_status()
    return r.json()


async def get_discord_user(access_token: str, *, http_client: httpx.AsyncClient) -> dict:
    r = await http_client.get(
        f"{DISCORD_API}/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    r.raise_for_status()
    return r.json()


async def get_discord_guilds(access_token: str, *, http_client: httpx.AsyncClient) -> list[dict]:
    r = await http_client.get(
        f"{DISCORD_API}/users/@me/guilds",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    r.raise_for_status()
    return r.json()


async def get_bot_user(bot_token: str, *, http_client: httpx.AsyncClient) -> dict:
    r = await http_client.get(
        f"{DISCORD_API}/users/@me",
        headers={"Authorization": f"Bot {bot_token}"},
    )
    r.raise_for_status()
    return r.json()


async def get_bot_guild_ids(bot_token: str, *, http_client: httpx.AsyncClient) -> set[str]:
    r = await http_client.get(
        f"{DISCORD_API}/users/@me/guilds",
        headers={"Authorization": f"Bot {bot_token}"},
    )
    r.raise_for_status()
    guilds = r.json()
    return {g["id"] for g in guilds if "id" in g}


def filter_managed_guilds(guilds: list[dict]) -> list[dict]:
    """Return only guilds where user has MANAGE_GUILD permission."""
    result = []
    for g in guilds:
        perms = int(g.get("permissions", "0"))
        if perms & MANAGE_GUILD:
            result.append({"id": g["id"], "name": g["name"], "icon": g.get("icon")})
    return result


def filter_bot_joined_guilds(
    guilds: list[dict],
    bot_guild_ids: set[str],
) -> list[dict]:
    """Return guilds where bot is present, with MANAGE_GUILD permission flag."""
    result = []
    for g in guilds:
        guild_id = g.get("id")
        if not guild_id or guild_id not in bot_guild_ids:
            continue
        perms = int(g.get("permissions", "0"))
        result.append(
            {
                "id": guild_id,
                "name": g["name"],
                "icon": g.get("icon"),
                "has_manage_guild": bool(perms & MANAGE_GUILD),
            }
        )
    return result

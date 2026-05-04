from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, fields as dc_fields
from pathlib import Path
from typing import get_origin, get_type_hints

# config.json は // スタイルのコメントを記述できます（JSONC 相当）
_COMMENT_RE = re.compile(
    r'"(?:[^"\\]|\\.)*"'  # 文字列リテラル（スキップ対象）
    r'|//[^\n]*',           # // ラインコメント（除去対象）
)


def _strip_comments(text: str) -> str:
    """JSON テキストから // コメントを除去する（文字列内の // は保持）。"""
    return _COMMENT_RE.sub(
        lambda m: m.group() if m.group().startswith('"') else "",
        text,
    )


def _strip_trailing_commas(text: str) -> str:
    """オブジェクト/配列末尾の余分なカンマを除去する（文字列内は保持）。"""
    out: list[str] = []
    in_string = False
    escaped = False
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue

        if ch == ",":
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j < n and text[j] in "]}":
                i += 1
                continue

        out.append(ch)
        i += 1

    return "".join(out)


@dataclass
class Config:
    discord_token: str
    encryption_master_key: str
    category_normalization: str = "reading"
    sentence_transformer_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    local_generation_model: str = "mistralai/Ministral-3-14B-Instruct-2512"
    huggingface_token: str = ""
    cpu_only_mode: bool = False
    delay_read_min: float = 10.0
    delay_read_max: float = 30.0
    delay_type_cps: float = 5.0
    conversation_log_retention_days: int = 7
    log_level: str = "INFO"
    db_path: str = "ideal_bot.db"
    web_url: str = "http://localhost:8000"
    # Web admin
    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_redirect_uri: str = "http://localhost:8000/auth/callback"
    session_secret: str = ""
    bot_admin_ids: list[str] = field(default_factory=list)
    web_host: str = "0.0.0.0"
    web_port: int = 8000
    frontend_url: str = ""  # 空の場合は web_url から導出
    # ログファイル設定（空文字の場合はファイル出力なし）
    log_file: str = ""
    log_max_bytes: int = 10 * 1024 * 1024  # 10 MB
    log_backup_count: int = 3


def _derive_defaults(cfg_data: dict, web_url: str) -> dict:
    """web_url を元に省略可能な項目を補完する。"""
    if not cfg_data.get("discord_redirect_uri"):
        cfg_data["discord_redirect_uri"] = web_url.rstrip("/") + "/auth/callback"
    if not cfg_data.get("frontend_url"):
        cfg_data["frontend_url"] = web_url
    return cfg_data


def load_config(path: str | Path = "config.json") -> Config:
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
            data = json.loads(_strip_trailing_commas(_strip_comments(text)))
    except FileNotFoundError:
        data = {}

    known = {f.name for f in dc_fields(Config)}
    cfg_data = {k: v for k, v in data.items() if k in known}

    # 環境変数でオーバーライド（フィールド名の大文字が環境変数名）
    # 例: DISCORD_TOKEN, DB_PATH, BOT_ADMIN_IDS (カンマ区切り)
    hints = get_type_hints(Config)
    for f in dc_fields(Config):
        env_key = f.name.upper()
        env_val = os.environ.get(env_key)
        if env_val is None:
            continue
        hint = hints.get(f.name)
        if get_origin(hint) is list:
            cfg_data[f.name] = [v.strip() for v in env_val.split(",") if v.strip()]
        elif hint is bool:
            cfg_data[f.name] = env_val.strip().lower() in ("1", "true", "yes", "on")
        elif hint is int:
            cfg_data[f.name] = int(env_val)
        elif hint is float:
            cfg_data[f.name] = float(env_val)
        else:
            cfg_data[f.name] = env_val

    web_url = cfg_data.get("web_url", "http://localhost:8000")
    cfg_data = _derive_defaults(cfg_data, web_url)

    # setup.sh may store numeric IDs; normalize to string for consistent comparisons.
    if "bot_admin_ids" in cfg_data and isinstance(cfg_data["bot_admin_ids"], list):
        cfg_data["bot_admin_ids"] = [str(v) for v in cfg_data["bot_admin_ids"]]

    return Config(**cfg_data)

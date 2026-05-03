from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest

from src.ai.generator import (
    _length_target_range,
    generate_response,
    generate_response_with_context,
)
from src.db import words as words_db

GUILD = "g1"
CHANNEL = "ch1"


def _make_config(master_key: str) -> MagicMock:
    cfg = MagicMock()
    cfg.encryption_master_key = master_key
    return cfg


def _make_local_ai(selected: list[str], can_generate: bool = False, generated: str = "") -> MagicMock:
    local_ai = MagicMock()
    local_ai.select_top_words_async = AsyncMock(return_value=selected)
    local_ai.can_generate = can_generate
    local_ai.generate_sentence_async = AsyncMock(return_value=(generated, "{}"))
    return local_ai


async def test_returns_fallback_response_when_no_words(db: aiosqlite.Connection):
    from cryptography.fernet import Fernet
    from src.db import fallback_responses as fallback_db

    cfg = _make_config(Fernet.generate_key().decode())
    local_ai = _make_local_ai([])

    result = await generate_response(
        db=db,
        config=cfg,
        local_ai=local_ai,
        guild_id=GUILD,
        channel_id=CHANNEL,
        bot_name="TestBot",
    )
    assert result in fallback_db.DEFAULT_FALLBACK_RESPONSES


async def test_generates_response_with_words(db: aiosqlite.Connection):
    from cryptography.fernet import Fernet

    await words_db.insert_word(
        db,
        guild_id=GUILD,
        word="りんご",
        reading="りんご",
        category="果物",
        category_reading="果物",
        added_by="user1",
    )

    cfg = _make_config(Fernet.generate_key().decode())
    local_ai = _make_local_ai(["りんご"])

    result = await generate_response(
        db=db,
        config=cfg,
        local_ai=local_ai,
        guild_id=GUILD,
        channel_id=CHANNEL,
        bot_name="TestBot",
        context_override=["テスト"],
    )
    assert "りんご" in result


async def test_theme_prepended_to_context(db: aiosqlite.Connection):
    """select_top_words_async should receive the theme as first context element."""
    from cryptography.fernet import Fernet

    await words_db.insert_word(
        db,
        guild_id=GUILD,
        word="みかん",
        reading="みかん",
        category="果物",
        category_reading="果物",
        added_by="u",
    )

    cfg = _make_config(Fernet.generate_key().decode())
    local_ai = _make_local_ai(["みかん"])

    await generate_response(
        db=db,
        config=cfg,
        local_ai=local_ai,
        guild_id=GUILD,
        channel_id=CHANNEL,
        bot_name="TestBot",
        theme="果物の話",
    )

    called_context = local_ai.select_top_words_async.call_args[0][0]
    assert called_context[0] == "果物の話"


async def test_uses_generation_model_when_available(db: aiosqlite.Connection):
    """When can_generate=True, result should come from generate_sentence_async."""
    from cryptography.fernet import Fernet

    await words_db.insert_word(
        db,
        guild_id=GUILD,
        word="バナナ",
        reading="ばなな",
        category="果物",
        category_reading="果物",
        added_by="u",
    )

    cfg = _make_config(Fernet.generate_key().decode())
    local_ai = _make_local_ai(
        ["バナナ"],
        can_generate=True,
        generated="バナナが好きだよ！",
    )

    result = await generate_response(
        db=db,
        config=cfg,
        local_ai=local_ai,
        guild_id=GUILD,
        channel_id=CHANNEL,
        bot_name="TestBot",
        context_override=["果物の話をしよう"],
    )
    assert result == "バナナが好きだよ！"
    local_ai.generate_sentence_async.assert_awaited_once()


async def test_falls_back_to_word_when_generation_returns_empty(db: aiosqlite.Connection):
    """If generate_sentence_async returns empty string, fall back to selected word."""
    from cryptography.fernet import Fernet

    await words_db.insert_word(
        db,
        guild_id=GUILD,
        word="ぶどう",
        reading="ぶどう",
        category="果物",
        category_reading="果物",
        added_by="u",
    )

    cfg = _make_config(Fernet.generate_key().decode())
    local_ai = _make_local_ai(["ぶどう"], can_generate=True, generated="")

    result = await generate_response(
        db=db,
        config=cfg,
        local_ai=local_ai,
        guild_id=GUILD,
        channel_id=CHANNEL,
        bot_name="TestBot",
    )
    assert result == "ぶどう"


async def test_returns_reply_context_snapshot(db: aiosqlite.Connection):
    from cryptography.fernet import Fernet

    await words_db.insert_word(
        db,
        guild_id=GUILD,
        word="りんご",
        reading="りんご",
        category="果物",
        category_reading="果物",
        added_by="user1",
    )
    from src.db import conversation_log as log_db

    await log_db.add_message(db, GUILD, CHANNEL, "user1", "こんにちは", is_bot=False)

    cfg = _make_config(Fernet.generate_key().decode())
    local_ai = _make_local_ai(["りんご"])

    _, reply_context, _ = await generate_response_with_context(
        db=db,
        config=cfg,
        local_ai=local_ai,
        guild_id=GUILD,
        channel_id=CHANNEL,
        bot_name="TestBot",
    )

    assert reply_context == "user: こんにちは"


def test_length_target_range_from_user_message():
    result = _length_target_range("こんにちは")
    assert result is not None
    target, min_len, max_len = result
    assert target == 5
    assert min_len <= target <= max_len


async def test_local_generation_receives_context_history(db: aiosqlite.Connection):
    from cryptography.fernet import Fernet
    from src.db import conversation_log as log_db

    await words_db.insert_word(
        db,
        guild_id=GUILD,
        word="りんご",
        reading="りんご",
        category="果物",
        category_reading="果物",
        added_by="user1",
    )
    await log_db.add_message(db, GUILD, CHANNEL, "user1", "おはよう", is_bot=False)

    cfg = _make_config(Fernet.generate_key().decode())
    local_ai = _make_local_ai(
        ["りんご"],
        can_generate=True,
        generated="りんごだよ。",
    )

    await generate_response(
        db=db,
        config=cfg,
        local_ai=local_ai,
        guild_id=GUILD,
        channel_id=CHANNEL,
        bot_name="TestBot",
    )

    kwargs = local_ai.generate_sentence_async.await_args.kwargs
    assert "target_length" not in kwargs
    assert kwargs["context_history"][-1] == (False, "おはよう")


# ---------------------------------------------------------------------------
# vLLM provider routing
# ---------------------------------------------------------------------------


async def test_vllm_provider_used_when_base_url_configured(db: aiosqlite.Connection):
    """When provider=vllm and vllm_base_url is set, VLLMProvider should be called."""
    from cryptography.fernet import Fernet
    from src.db import bot_settings as bot_settings_db

    await words_db.insert_word(
        db, guild_id=GUILD, word="テスト", reading="てすと",
        category="c", category_reading="c", added_by="u",
    )
    await bot_settings_db.set_value(db, "global_llm_provider", "vllm")
    await bot_settings_db.set_value(db, "vllm_base_url", "http://localhost:8000/v1")
    await bot_settings_db.set_value(db, "global_llm_model", "test-model")

    cfg = _make_config(Fernet.generate_key().decode())
    local_ai = _make_local_ai(["テスト"])

    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value="vLLM response")

    with patch("src.ai.llm.vllm_provider.VLLMProvider", return_value=mock_provider) as mock_cls:
        result = await generate_response(
            db=db, config=cfg, local_ai=local_ai,
            guild_id=GUILD, channel_id=CHANNEL, bot_name="TestBot",
        )

    assert result == "vLLM response"
    mock_cls.assert_called_once_with(base_url="http://localhost:8000/v1", model="test-model")


async def test_vllm_falls_back_to_local_when_no_base_url(db: aiosqlite.Connection):
    """provider=vllm with no vllm_base_url should not call VLLMProvider."""
    from cryptography.fernet import Fernet
    from src.db import bot_settings as bot_settings_db

    await words_db.insert_word(
        db, guild_id=GUILD, word="テスト", reading="てすと",
        category="c", category_reading="c", added_by="u",
    )
    await bot_settings_db.set_value(db, "global_llm_provider", "vllm")
    # vllm_base_url intentionally not set

    cfg = _make_config(Fernet.generate_key().decode())
    local_ai = _make_local_ai(["テスト"])

    with patch("src.ai.llm.vllm_provider.VLLMProvider") as mock_cls:
        result = await generate_response(
            db=db, config=cfg, local_ai=local_ai,
            guild_id=GUILD, channel_id=CHANNEL, bot_name="TestBot",
        )

    mock_cls.assert_not_called()
    assert result == "テスト"


async def test_vllm_falls_back_to_local_when_provider_returns_empty(db: aiosqlite.Connection):
    """Empty vLLM response should fall through to local AI."""
    from cryptography.fernet import Fernet
    from src.db import bot_settings as bot_settings_db

    await words_db.insert_word(
        db, guild_id=GUILD, word="テスト", reading="てすと",
        category="c", category_reading="c", added_by="u",
    )
    await bot_settings_db.set_value(db, "global_llm_provider", "vllm")
    await bot_settings_db.set_value(db, "vllm_base_url", "http://localhost:8000/v1")
    await bot_settings_db.set_value(db, "global_llm_model", "test-model")

    cfg = _make_config(Fernet.generate_key().decode())
    local_ai = _make_local_ai(["テスト"])

    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value="")

    with patch("src.ai.llm.vllm_provider.VLLMProvider", return_value=mock_provider):
        result = await generate_response(
            db=db, config=cfg, local_ai=local_ai,
            guild_id=GUILD, channel_id=CHANNEL, bot_name="TestBot",
        )

    assert result == "テスト"

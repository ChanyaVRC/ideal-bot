from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

import aiosqlite

from src.db import bot_settings as bot_settings_db
from src.db import conversation_log as log_db
from src.db import fallback_responses as fallback_db
from src.db import guild_settings as settings_db
from src.db import words as words_db
from src.utils.encryption import decrypt

if TYPE_CHECKING:
    from src.ai.local import LocalAI
    from src.config import Config

logger = logging.getLogger(__name__)


def _find_latest_user_text(
    *,
    context_messages: list,
    context_override: list[str] | None,
) -> str:
    if context_override:
        return context_override[-1]
    for message in reversed(context_messages):
        if not message.is_bot:
            return message.content
    return ""


def _length_target_range(latest_user_text: str) -> tuple[int, int, int] | None:
    if not latest_user_text:
        return None
    target = max(4, len(latest_user_text.strip()))
    min_len = max(4, int(target * 0.7))
    max_len = max(min_len + 4, int(target * 1.3))
    return target, min_len, max_len


def _format_message_context_snapshot(context: list, theme: str | None) -> str | None:
    lines: list[str] = []
    if theme:
        lines.append(f"theme: {theme}")
    lines.extend(
        f"{'assistant' if message.is_bot else 'user'}: {message.content}"
        for message in context
    )
    return "\n".join(lines) or None


def _format_text_context_snapshot(
    context: list[str],
    *,
    theme: str | None,
    uses_override: bool,
) -> str | None:
    lines: list[str] = []
    if theme:
        lines.append(f"theme: {theme}")

    label = "context" if uses_override else "user"
    lines.extend(f"{label}: {text}" for text in context)
    return "\n".join(lines) or None


async def generate_response(
    *,
    db: aiosqlite.Connection,
    config: "Config",
    local_ai: "LocalAI",
    guild_id: str,
    channel_id: str,
    bot_name: str,
    context_override: list[str] | None = None,
    theme: str | None = None,
) -> str:
    response, _, _metadata = await generate_response_with_context(
        db=db,
        config=config,
        local_ai=local_ai,
        guild_id=guild_id,
        channel_id=channel_id,
        bot_name=bot_name,
        context_override=context_override,
        theme=theme,
    )
    return response


async def generate_response_with_context(
    *,
    db: aiosqlite.Connection,
    config: "Config",
    local_ai: "LocalAI",
    guild_id: str,
    channel_id: str,
    bot_name: str,
    context_override: list[str] | None = None,
    theme: str | None = None,
) -> tuple[str, str | None, str | None]:
    """Generate response with context and metadata.
    
    Returns:
        tuple[str, str | None, str | None]: (response, reply_context, generation_metadata_json)
    """
    settings = await settings_db.ensure_settings(db, guild_id)

    llm_key, llm_provider, llm_model = await _resolve_llm(db, config, settings)

    context_messages = await log_db.get_recent_messages(
        db, guild_id, channel_id, limit=settings.context_count
    )
    latest_user_text = _find_latest_user_text(
        context_messages=context_messages,
        context_override=context_override,
    )
    target_range = _length_target_range(latest_user_text)

    vllm_base_url = (
        await bot_settings_db.get_value(db, "vllm_base_url") if llm_provider == "vllm" else None
    )
    if llm_key or (llm_provider == "vllm" and vllm_base_url):
        try:
            response = await _generate_llm(
                llm_key=llm_key,
                vllm_base_url=vllm_base_url,
                provider=llm_provider,
                model=llm_model,
                persona=settings.bot_persona or "",
                bot_name=bot_name,
                context=context_messages,
                db=db,
                guild_id=guild_id,
                theme=theme,
                target_range=target_range,
            )
            if response:
                return response, _format_message_context_snapshot(context_messages, theme), None
            logger.warning("LLM returned empty response, falling back to local AI")
        except Exception:
            logger.exception("LLM generation failed, falling back to local AI")

    system_prompt_tpl = await bot_settings_db.get_value(db, "local_system_prompt") or None
    # 会話履歴（user/assistant 交互）を構築してローカル LLM に渡す
    # context_override が指定された場合はそれを user メッセージとして history に変換
    if context_override:
        context_history: list[tuple[bool, str]] = [(False, text) for text in context_override]
    else:
        context_history = [(m.is_bot, m.content) for m in context_messages]
    if theme:
        context_history = [(False, theme)] + context_history
    response, metadata = await _generate_local(
        db=db,
        local_ai=local_ai,
        guild_id=guild_id,
        bot_name=bot_name,
        system_prompt_tpl=system_prompt_tpl,
        context_history=context_history,
    )
    if context_override:
        reply_context = _format_text_context_snapshot(
            context_override,
            theme=theme,
            uses_override=True,
        )
    else:
        reply_context = _format_message_context_snapshot(context_messages, theme)
    return response, reply_context, metadata


async def _resolve_llm(
    db: aiosqlite.Connection, config: "Config", settings: settings_db.GuildSettings
) -> tuple[str | None, str, str]:
    if settings.llm_api_key:
        try:
            return decrypt(config.encryption_master_key, settings.llm_api_key), settings.llm_provider, settings.llm_model
        except Exception:
            pass

    global_key_enc = await bot_settings_db.get_value(db, "global_llm_api_key")
    global_provider = await bot_settings_db.get_value(db, "global_llm_provider") or "openai"
    global_model = await bot_settings_db.get_value(db, "global_llm_model") or "gpt-4o-mini"
    if global_key_enc:
        try:
            return decrypt(config.encryption_master_key, global_key_enc), global_provider, global_model
        except Exception:
            pass

    # vLLM requires no API key; use global provider/model when configured globally.
    if global_provider == "vllm":
        return None, global_provider, global_model

    return None, settings.llm_provider, settings.llm_model


async def _generate_local(
    *,
    db: aiosqlite.Connection,
    local_ai: "LocalAI",
    guild_id: str,
    bot_name: str = "Bot",
    system_prompt_tpl: str | None = None,
    context_history: list[tuple[bool, str]] | None = None,
) -> tuple[str, str | None]:
    """Generate response locally.
    
    Returns:
        tuple[str, str | None]: (response_text, generation_metadata_json)
    """
    all_words = await words_db.get_words(db, guild_id)
    if not all_words:
        fallback_responses = await fallback_db.get_fallback_responses(db)
        return random.choice(fallback_responses), None

    word_pairs = [(w.word, w.embedding) for w in all_words]
    word_context = [text for is_bot, text in (context_history or []) if not is_bot]
    if word_context:
        selected = await local_ai.select_top_words_async(word_context, word_pairs, top_k=5)
    else:
        selected = [w.word for w in random.sample(all_words, min(5, len(all_words)))]

    if not selected:
        selected = [random.choice(all_words).word]

    if local_ai.can_generate:
        sentence, metadata = await local_ai.generate_sentence_async(
            selected,
            bot_name=bot_name,
            system_prompt_tpl=system_prompt_tpl,
            context_history=context_history,
        )
        if sentence:
            return sentence, metadata

    return random.choice(selected), None


async def _generate_llm(
    *,
    llm_key: str | None,
    vllm_base_url: str | None = None,
    provider: str,
    model: str,
    persona: str,
    bot_name: str,
    context: list,
    db: aiosqlite.Connection,
    guild_id: str,
    theme: str | None,
    target_range: tuple[int, int, int] | None,
) -> str:
    all_words = await words_db.get_words(db, guild_id)
    word_list = "、".join(w.word for w in all_words[:80])

    system = (
        f'あなたは「{bot_name}」というキャラクターです。\n'
        f'以下の単語を知っています: {word_list}\n'
        f'口調: {persona}'
    )
    if theme:
        system += f'\nテーマ: {theme}'
    if target_range:
        target, min_len, max_len = target_range
        system += (
            f"\n返答の長さは直近ユーザー発言（約{target}文字）に近づけ、"
            f"{min_len}〜{max_len}文字を目安にしてください。"
        )

    messages = [
        {"role": "assistant" if m.is_bot else "user", "content": m.content}
        for m in context
    ]

    if provider == "openai":
        from src.ai.llm.openai_provider import OpenAIProvider
        llm = OpenAIProvider(api_key=llm_key or "", model=model)
    elif provider == "gemini":
        from src.ai.llm.gemini_provider import GeminiProvider
        llm = GeminiProvider(api_key=llm_key or "", model=model)
    elif provider == "vllm":
        from src.ai.llm.vllm_provider import VLLMProvider
        if not vllm_base_url:
            raise ValueError("vllm_base_url is required for vllm provider")
        llm = VLLMProvider(base_url=vllm_base_url, model=model)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    return await llm.generate(messages=messages, system=system)

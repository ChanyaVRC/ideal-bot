from __future__ import annotations

import asyncio
import functools

import aiosqlite
import numpy as np

from src.db import words as words_db
from src.utils.reading import to_reading

# vector モードでの類似カテゴリ判定閾値（コサイン類似度）
VECTOR_SIMILARITY_THRESHOLD = 0.85


def get_word_reading(mode: str, word: str) -> str:
    """単語の重複判定キーを返す。

    - reading : pykakasi でひらがな読みに変換（デフォルト）
    - word    : 表記そのまま（完全一致）
    - vector  : reading と同じ（単語は常に reading キーで管理）
    """
    if mode == "word":
        return word
    return to_reading(word)


def get_category_reading(mode: str, category: str) -> str:
    """カテゴリの重複判定キーを返す。

    - reading : pykakasi でひらがな読みに変換
    - word    : 表記そのまま（完全一致）
    - vector  : 読みキーを使用（解決は resolve_category で行う）
    """
    if mode == "word":
        return category
    return to_reading(category)


async def resolve_category(
    mode: str,
    local_ai,
    db: aiosqlite.Connection,
    guild_id: str,
    category: str,
) -> tuple[str, str]:
    """カテゴリ名と category_reading キーの組を返す。

    vector モードでは既存カテゴリとの類似度を計算し、閾値以上であれば
    既存カテゴリ名・キーに統合する。それ以外のモードは即座に返す。

    Returns:
        (resolved_category_name, category_reading)
    """
    if mode == "vector" and local_ai is not None:
        matched = await _find_similar_category(local_ai, db, guild_id, category)
        if matched is not None:
            return matched

    return category, get_category_reading(mode, category)


async def _find_similar_category(
    local_ai,
    db: aiosqlite.Connection,
    guild_id: str,
    category: str,
) -> tuple[str, str] | None:
    """既存カテゴリの中から最も類似するものを返す。閾値未満なら None。"""
    existing = await words_db.get_categories(db, guild_id)
    if not existing:
        return None

    cat_names = [cat_name for cat_name, _ in existing]
    # 既存カテゴリと入力を一括エンコード（N+1 回 → 1 回）
    all_texts = cat_names + [category]
    loop = asyncio.get_event_loop()
    all_embs: np.ndarray = await loop.run_in_executor(
        None,
        functools.partial(local_ai._ensure_model().encode, all_texts, normalize_embeddings=True),
    )
    new_emb = all_embs[-1]
    cat_embs = all_embs[:-1]

    scores = cat_embs @ new_emb
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])

    if best_score >= VECTOR_SIMILARITY_THRESHOLD:
        cat_name = cat_names[best_idx]
        cat_reading = existing[best_idx][1]
        return (cat_name, cat_reading)

    return None

from __future__ import annotations

import pytest
import aiosqlite

from src.db import words as words_db

GUILD = "guild1"


async def _insert(db: aiosqlite.Connection, word: str, reading: str, category: str = "食べ物") -> None:
    await words_db.insert_word(
        db,
        guild_id=GUILD,
        word=word,
        reading=reading,
        category=category,
        category_reading=category,
        added_by="user1",
    )


async def test_insert_and_get(db: aiosqlite.Connection):
    await _insert(db, "りんご", "りんご")
    row = await words_db.get_word_by_reading(db, GUILD, "りんご")
    assert row is not None
    assert row.word == "りんご"
    assert row.embedding is None


async def test_insert_with_embedding(db: aiosqlite.Connection):
    emb = b"\x00\x01\x02\x03"
    await words_db.insert_word(
        db,
        guild_id=GUILD,
        word="みかん",
        reading="みかん",
        category="食べ物",
        category_reading="食べ物",
        added_by="user1",
        embedding=emb,
    )
    row = await words_db.get_word_by_reading(db, GUILD, "みかん")
    assert row is not None
    assert row.embedding == emb


async def test_upsert_overwrites(db: aiosqlite.Connection):
    await _insert(db, "バナナ", "ばなな")
    await words_db.upsert_word(
        db,
        guild_id=GUILD,
        word="バナナ（熟）",
        reading="ばなな",
        category="食べ物",
        category_reading="食べ物",
        added_by="user2",
    )
    row = await words_db.get_word_by_reading(db, GUILD, "ばなな")
    assert row is not None
    assert row.word == "バナナ（熟）"
    assert row.added_by == "user2"


async def test_get_words_all(db: aiosqlite.Connection):
    await _insert(db, "りんご", "りんご", "果物")
    await _insert(db, "みかん", "みかん", "果物")
    rows = await words_db.get_words(db, GUILD)
    assert len(rows) == 2


async def test_get_words_by_category(db: aiosqlite.Connection):
    await _insert(db, "りんご", "りんご", "果物")
    await _insert(db, "にんじん", "にんじん", "野菜")
    rows = await words_db.get_words(db, GUILD, category_reading="果物")
    assert len(rows) == 1
    assert rows[0].word == "りんご"


async def test_delete_word(db: aiosqlite.Connection):
    await _insert(db, "ぶどう", "ぶどう")
    await words_db.delete_word_by_reading(db, GUILD, "ぶどう")
    assert await words_db.get_word_by_reading(db, GUILD, "ぶどう") is None


async def test_get_categories(db: aiosqlite.Connection):
    await _insert(db, "りんご", "りんご", "果物")
    await _insert(db, "みかん", "みかん", "果物")
    await _insert(db, "にんじん", "にんじん", "野菜")
    cats = await words_db.get_categories(db, GUILD)
    assert len(cats) == 2


async def test_insert_duplicate_reading_raises(db: aiosqlite.Connection):
    await _insert(db, "りんご", "りんご")
    with pytest.raises(Exception):
        await _insert(db, "林檎", "りんご")

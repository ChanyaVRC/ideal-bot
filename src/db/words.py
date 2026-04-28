from __future__ import annotations

from dataclasses import dataclass

import aiosqlite


@dataclass
class Word:
    id: int
    guild_id: str
    word: str
    reading: str
    category: str
    category_reading: str
    added_by: str
    embedding: bytes | None
    created_at: str


async def get_word_by_reading(
    db: aiosqlite.Connection, guild_id: str, reading: str
) -> Word | None:
    async with db.execute(
        "SELECT * FROM words WHERE guild_id = ? AND reading = ?",
        (guild_id, reading),
    ) as cursor:
        row = await cursor.fetchone()
    return Word(**dict(row)) if row else None


async def get_words(
    db: aiosqlite.Connection,
    guild_id: str,
    category_reading: str | None = None,
) -> list[Word]:
    if category_reading is not None:
        async with db.execute(
            "SELECT * FROM words WHERE guild_id = ? AND category_reading = ? ORDER BY created_at DESC",
            (guild_id, category_reading),
        ) as cursor:
            rows = await cursor.fetchall()
    else:
        async with db.execute(
            "SELECT * FROM words WHERE guild_id = ? ORDER BY created_at DESC",
            (guild_id,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [Word(**dict(row)) for row in rows]


async def get_categories(
    db: aiosqlite.Connection, guild_id: str
) -> list[tuple[str, str]]:
    """Returns list of (category, category_reading) pairs."""
    async with db.execute(
        "SELECT DISTINCT category, category_reading FROM words WHERE guild_id = ? ORDER BY category",
        (guild_id,),
    ) as cursor:
        rows = await cursor.fetchall()
    return [(row["category"], row["category_reading"]) for row in rows]


async def get_all_words_for_autocomplete(
    db: aiosqlite.Connection, guild_id: str
) -> list[tuple[str, str]]:
    """Returns list of (word, reading) pairs for autocomplete."""
    async with db.execute(
        "SELECT word, reading FROM words WHERE guild_id = ? ORDER BY word",
        (guild_id,),
    ) as cursor:
        rows = await cursor.fetchall()
    return [(row["word"], row["reading"]) for row in rows]


async def insert_word(
    db: aiosqlite.Connection,
    *,
    guild_id: str,
    word: str,
    reading: str,
    category: str,
    category_reading: str,
    added_by: str,
    embedding: bytes | None = None,
) -> None:
    await db.execute(
        """
        INSERT INTO words (guild_id, word, reading, category, category_reading, added_by, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (guild_id, word, reading, category, category_reading, added_by, embedding),
    )
    await db.commit()


async def upsert_word(
    db: aiosqlite.Connection,
    *,
    guild_id: str,
    word: str,
    reading: str,
    category: str,
    category_reading: str,
    added_by: str,
    embedding: bytes | None = None,
) -> None:
    await db.execute(
        """
        INSERT INTO words (guild_id, word, reading, category, category_reading, added_by, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (guild_id, reading) DO UPDATE SET
            word             = excluded.word,
            category         = excluded.category,
            category_reading = excluded.category_reading,
            added_by         = excluded.added_by,
            embedding        = excluded.embedding
        """,
        (guild_id, word, reading, category, category_reading, added_by, embedding),
    )
    await db.commit()


async def delete_word_by_reading(
    db: aiosqlite.Connection, guild_id: str, reading: str
) -> bool:
    cursor = await db.execute(
        "DELETE FROM words WHERE guild_id = ? AND reading = ?",
        (guild_id, reading),
    )
    await db.commit()
    return cursor.rowcount > 0

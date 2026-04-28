from __future__ import annotations

import aiosqlite

DEFAULT_FALLBACK_RESPONSES = [
    "まだ言葉を知らないよ…/teach で教えてほしいな",
    "何も知らなくてごめんね。/teach で言葉を教えてくれると嬉しい！",
    "言葉が足りなくて何も言えない…/teach で教えて？",
    "もっとしゃべりたいけど言葉がないよ。/teach で教えてほしい！",
    "うまく話せない…/teach でいろんな言葉を教えてほしいな",
]


async def get_fallback_responses(db: aiosqlite.Connection) -> list[str]:
    async with db.execute(
        "SELECT response FROM fallback_responses ORDER BY sort_order, id"
    ) as cursor:
        rows = await cursor.fetchall()
    if not rows:
        return DEFAULT_FALLBACK_RESPONSES
    return [row["response"] for row in rows]


async def list_fallback_responses(db: aiosqlite.Connection) -> list[tuple[int, str, int, str]]:
    async with db.execute(
        "SELECT id, response, sort_order, created_at FROM fallback_responses ORDER BY sort_order, id"
    ) as cursor:
        rows = await cursor.fetchall()
    return [
        (row["id"], row["response"], row["sort_order"], row["created_at"])
        for row in rows
    ]


async def add_fallback_response(
    db: aiosqlite.Connection, response: str, sort_order: int | None = None
) -> int:
    order = sort_order
    if order is None:
        async with db.execute(
            "SELECT COALESCE(MAX(sort_order), 0) AS max_order FROM fallback_responses"
        ) as cursor:
            row = await cursor.fetchone()
        order = int(row["max_order"]) + 10

    cursor = await db.execute(
        "INSERT INTO fallback_responses (response, sort_order) VALUES (?, ?)",
        (response, order),
    )
    await db.commit()
    return cursor.lastrowid


async def delete_fallback_response(db: aiosqlite.Connection, response_id: int) -> bool:
    cursor = await db.execute(
        "DELETE FROM fallback_responses WHERE id = ?",
        (response_id,),
    )
    await db.commit()
    return cursor.rowcount > 0

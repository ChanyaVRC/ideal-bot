from __future__ import annotations

import aiosqlite

from src.db import conversation_log as log_db

GUILD = "g1"
CHANNEL = "ch1"


async def test_add_and_retrieve(db: aiosqlite.Connection):
    await log_db.add_message(db, GUILD, CHANNEL, "user1", "こんにちは", is_bot=False)
    messages = await log_db.get_recent_messages(db, GUILD, CHANNEL, limit=10)
    assert len(messages) == 1
    assert messages[0].content == "こんにちは"
    assert messages[0].is_bot is False


async def test_is_bot_flag(db: aiosqlite.Connection):
    await log_db.add_message(db, GUILD, CHANNEL, "bot", "やあ", is_bot=True)
    messages = await log_db.get_recent_messages(db, GUILD, CHANNEL, limit=10)
    assert messages[0].is_bot is True


async def test_reply_context_is_stored(db: aiosqlite.Connection):
    await log_db.add_message(
        db,
        GUILD,
        CHANNEL,
        "bot",
        "やあ",
        is_bot=True,
        reply_context="user: こんにちは",
    )
    messages = await log_db.get_recent_messages(db, GUILD, CHANNEL, limit=10)
    assert messages[0].reply_context == "user: こんにちは"


async def test_limit_respected(db: aiosqlite.Connection):
    for i in range(5):
        await log_db.add_message(db, GUILD, CHANNEL, "user1", f"msg{i}", is_bot=False)
    messages = await log_db.get_recent_messages(db, GUILD, CHANNEL, limit=3)
    assert len(messages) == 3


async def test_channel_isolation(db: aiosqlite.Connection):
    await log_db.add_message(db, GUILD, "ch_a", "user1", "ch_a msg", is_bot=False)
    await log_db.add_message(db, GUILD, "ch_b", "user1", "ch_b msg", is_bot=False)
    msgs_a = await log_db.get_recent_messages(db, GUILD, "ch_a", limit=10)
    assert len(msgs_a) == 1
    assert msgs_a[0].content == "ch_a msg"


async def test_purge_channel(db: aiosqlite.Connection):
    for i in range(25):
        await log_db.add_message(db, GUILD, CHANNEL, "u", f"m{i}", is_bot=False)
    await log_db.purge_channel(db, GUILD, CHANNEL, max_count=20)
    messages = await log_db.get_recent_messages(db, GUILD, CHANNEL, limit=100)
    assert len(messages) <= 20

-- v1: 初期スキーマ

CREATE TABLE IF NOT EXISTS words (
    id               INTEGER PRIMARY KEY,
    guild_id         TEXT NOT NULL,
    word             TEXT NOT NULL,
    reading          TEXT NOT NULL,
    category         TEXT NOT NULL,
    category_reading TEXT NOT NULL,
    added_by         TEXT NOT NULL,
    embedding        BLOB,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (guild_id, reading)
);

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id         TEXT PRIMARY KEY,
    reply_rate       INTEGER DEFAULT 10,
    bot_enabled      BOOLEAN DEFAULT TRUE,
    llm_api_key      TEXT,
    llm_provider     TEXT DEFAULT 'openai',
    llm_model        TEXT DEFAULT 'gpt-4o-mini',
    bot_persona      TEXT,
    context_count    INTEGER DEFAULT 10,
    conversation_ttl INTEGER DEFAULT 5,
    delay_read_min   REAL,
    delay_read_max   REAL,
    delay_type_cps   REAL
);

CREATE TABLE IF NOT EXISTS teach_allowlist (
    id          INTEGER PRIMARY KEY,
    guild_id    TEXT NOT NULL,
    target_id   TEXT NOT NULL,
    target_type TEXT NOT NULL CHECK (target_type IN ('role', 'user'))
);

CREATE TABLE IF NOT EXISTS conversation_log (
    id         INTEGER PRIMARY KEY,
    guild_id   TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    author_id  TEXT NOT NULL,
    content    TEXT NOT NULL,
    is_bot     BOOLEAN DEFAULT FALSE,
    reply_context TEXT,
    generation_metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fallback_responses (
    id         INTEGER PRIMARY KEY,
    response   TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS discord_guild_cache (
    guild_id      TEXT PRIMARY KEY,
    name          TEXT NOT NULL DEFAULT '',
    icon          TEXT,
    is_bot_member INTEGER NOT NULL DEFAULT 0,
    cached_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO fallback_responses (response, sort_order)
SELECT 'まだ言葉を知らないよ…/teach で教えてほしいな', 10
WHERE NOT EXISTS (SELECT 1 FROM fallback_responses);

INSERT INTO fallback_responses (response, sort_order)
SELECT '何も知らなくてごめんね。/teach で言葉を教えてくれると嬉しい！', 20
WHERE NOT EXISTS (SELECT 1 FROM fallback_responses WHERE sort_order = 20);

INSERT INTO fallback_responses (response, sort_order)
SELECT '言葉が足りなくて何も言えない…/teach で教えて？', 30
WHERE NOT EXISTS (SELECT 1 FROM fallback_responses WHERE sort_order = 30);

INSERT INTO fallback_responses (response, sort_order)
SELECT 'もっとしゃべりたいけど言葉がないよ。/teach で教えてほしい！', 40
WHERE NOT EXISTS (SELECT 1 FROM fallback_responses WHERE sort_order = 40);

INSERT INTO fallback_responses (response, sort_order)
SELECT 'うまく話せない…/teach でいろんな言葉を教えてほしいな', 50
WHERE NOT EXISTS (SELECT 1 FROM fallback_responses WHERE sort_order = 50);

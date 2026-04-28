# ギルドエンドポイント (`/api/guilds/*`)

[← API 概要](./api)

すべてのエンドポイントで **要ギルド権限**（ログイン済み、かつ対象ギルドの MANAGE_GUILD 権限が必要）。

---

### `GET /api/guilds/{guild_id}/settings`

ギルド設定を取得します。

**レスポンス:**
```json
{
  "guild_id": "111111111111111111",
  "reply_rate": 10,
  "bot_enabled": true,
  "llm_provider": "openai",
  "llm_model": "gpt-4o-mini",
  "bot_persona": null,
  "context_count": 10,
  "conversation_ttl": 5,
  "delay_read_min": 10.0,
  "delay_read_max": 30.0,
  "delay_type_cps": 5.0,
  "has_api_key": false
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `reply_rate` | int | ランダム返信確率（0〜100%） |
| `bot_enabled` | boolean | このギルドで Bot を有効にするか |
| `llm_provider` | string | `"openai"` または `"gemini"` |
| `llm_model` | string | 使用するモデル名 |
| `bot_persona` | string \| null | Bot のキャラクター・口調設定 |
| `context_count` | int | 会話コンテキストとして参照する直近メッセージ数 |
| `conversation_ttl` | int | 会話モードのタイムアウト（分） |
| `delay_read_min` | float \| null | 読み取り遅延の最小秒数（null でグローバル設定を使用） |
| `delay_read_max` | float \| null | 読み取り遅延の最大秒数（null でグローバル設定を使用） |
| `delay_type_cps` | float \| null | タイピング速度（文字/秒、null でグローバル設定を使用） |
| `has_api_key` | boolean | このギルド専用の LLM API キーが設定済みか |

---

### `PATCH /api/guilds/{guild_id}/settings`

ギルド設定を部分更新します。指定したフィールドのみ更新されます。

**リクエストボディ（すべて省略可能）:**
```json
{
  "reply_rate": 20,
  "bot_enabled": true,
  "llm_provider": "openai",
  "llm_model": "gpt-4o-mini",
  "bot_persona": "フレンドリーな口調で話してください",
  "context_count": 10,
  "conversation_ttl": 5,
  "delay_read_min": 10.0,
  "delay_read_max": 30.0,
  "delay_type_cps": 5.0,
  "llm_api_key": "sk-..."
}
```

> `llm_api_key` は受信後に Fernet で暗号化して保存されます。空文字列 `""` を送ると既存キーを削除します。

**レスポンス:**
```json
{ "ok": true }
```

---

### `GET /api/guilds/{guild_id}/words`

登録語彙一覧を返します。

**レスポンス:**
```json
[
  {
    "word": "ふわふわ",
    "reading": "ふわふわ",
    "category": "形容詞",
    "category_reading": "けいようし",
    "added_by": "123456789",
    "created_at": "2026-04-28T10:00:00"
  }
]
```

---

### `DELETE /api/guilds/{guild_id}/words/{reading}`

指定した reading キーの単語を削除します。

**パスパラメータ:** `reading` — 削除する単語の reading キー（URL エンコード必要）  
**レスポンス:** `200 OK` `{ "ok": true }` または `404 Not Found`

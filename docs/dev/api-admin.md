# 管理者エンドポイント (`/api/admin/*`)

[← API 概要](./api)

すべてのエンドポイントで **要 Bot 管理者**（`config.json` の `bot_admin_ids` に登録済みのユーザーのみ）。

---

### `GET /api/admin/settings`

グローバル Bot 設定を取得します。

**レスポンス:**
```json
{
  "has_global_api_key": false,
  "global_llm_provider": "openai",
  "global_llm_model": "gpt-4o-mini",
  "discord_cache_ttl": 300,
  "local_system_prompt": "あなたは「{bot_name}」です..."
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `has_global_api_key` | boolean | グローバル LLM API キーが設定済みか |
| `global_llm_provider` | string | グローバルデフォルトのプロバイダー |
| `global_llm_model` | string | グローバルデフォルトのモデル |
| `discord_cache_ttl` | int | Discord ギルド情報のキャッシュ TTL（秒） |
| `local_system_prompt` | string | ローカル LLM 用システムプロンプトテンプレート（変数: `{bot_name}`, `{target_length}`） |

---

### `PATCH /api/admin/settings`

グローバル Bot 設定を部分更新します。

**リクエストボディ（すべて省略可能）:**
```json
{
  "global_llm_api_key": "sk-...",
  "global_llm_provider": "openai",
  "global_llm_model": "gpt-4o-mini",
  "discord_cache_ttl": 300,
  "local_system_prompt": "あなたは「{bot_name}」です..."
}
```

> `global_llm_api_key` は Fernet で暗号化して保存されます。空文字列 `""` を送ると既存キーを削除します。

**レスポンス:**
```json
{ "ok": true }
```

---

### `GET /api/admin/guilds`

全ギルドの一覧と Bot 有効状態を返します。

**レスポンス:**
```json
[
  {
    "guild_id": "111111111111111111",
    "bot_enabled": true,
    "name": "My Server",
    "icon": "icon_hash"
  }
]
```

---

### `PATCH /api/admin/guilds/{guild_id}`

指定ギルドの Bot 有効/無効を切り替えます。

**リクエストボディ:**
```json
{ "bot_enabled": false }
```

**レスポンス:**
```json
{ "ok": true }
```

---

### `GET /api/admin/logs`

会話ログを取得します。

**クエリパラメータ:**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `limit` | int | `100` | 取得件数（1〜500） |
| `offset` | int | `0` | オフセット（ページネーション用） |
| `guild_id` | string | — | 指定時はそのギルドのみ絞り込み |

**レスポンス:**
```json
[
  {
    "id": 1,
    "guild_id": "111111111111111111",
    "channel_id": "222222222222222222",
    "author_id": "333333333333333333",
    "content": "こんにちは",
    "is_bot": false,
    "reply_context": "user: こんにちは\nassistant: やあ！",
    "generation_metadata": null,
    "created_at": "2026-04-28T10:00:00"
  }
]
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `is_bot` | boolean | Bot の発言かどうか |
| `reply_context` | string \| null | 返答生成時に参照したコンテキスト（`user:`/`assistant:` ラベル付き） |
| `generation_metadata` | string \| null | ローカル LLM 生成時の出力辞書（JSON 文字列） |

---

### `GET /api/admin/fallback-responses`

ローカル語彙ゼロ時に使うフォールバック応答の一覧を返します。

**レスポンス:**
```json
[
  { "id": 1, "response": "うーん、わからない", "sort_order": 0, "created_at": "2026-04-28T10:00:00" }
]
```

---

### `POST /api/admin/fallback-responses`

フォールバック応答を追加します。

**リクエストボディ:**
```json
{ "response": "うーん、わからない" }
```

**レスポンス:** 作成された応答オブジェクト
```json
{ "id": 2, "response": "うーん、わからない", "sort_order": 1, "created_at": "2026-04-28T10:01:00" }
```

---

### `DELETE /api/admin/fallback-responses/{response_id}`

フォールバック応答を削除します。

**レスポンス:** `200 OK` `{ "ok": true }` または `404 Not Found`

---

### `POST /api/admin/sync-commands`

Bot にスラッシュコマンドの再同期を要求します。Bot が次回ポーリング時（最大 30 秒程度）に `tree.sync()` を実行します。

**レスポンス:**
```json
{ "ok": true }
```

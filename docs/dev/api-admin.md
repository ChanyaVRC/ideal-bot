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
  "cpu_only_mode": false,
  "local_system_prompt": "あなたは「{bot_name}」です...",
  "local_torch_dtype": "auto",
  "local_supported_torch_dtypes": ["auto", "float32", "bfloat16", "float16"],
  "local_quantization_mode": "none",
  "vllm_base_url": ""
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `has_global_api_key` | boolean | グローバル LLM API キーが設定済みか |
| `global_llm_provider` | string | グローバルデフォルトのプロバイダー |
| `global_llm_model` | string | グローバルデフォルトのモデル |
| `discord_cache_ttl` | int | Discord ギルド情報のキャッシュ TTL（秒） |
| `cpu_only_mode` | boolean | CPU のみモードが有効か（`config.json` の設定を反映） |
| `local_system_prompt` | string | ローカル LLM 用システムプロンプトテンプレート（変数: `{bot_name}`, `{target_length}`） |
| `local_torch_dtype` | string | ローカル生成モデルの torch dtype（例: `"auto"`, `"float16"`, `"bfloat16"`） |
| `local_supported_torch_dtypes` | string[] | 現在の環境で使用可能な dtype 一覧 |
| `local_quantization_mode` | string | 量子化モード（`"none"` / `"4bit"` / `"8bit"`） |
| `vllm_base_url` | string | vLLM エンドポイント URL（未設定時は空文字） |

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
  "local_system_prompt": "あなたは「{bot_name}」です...",
  "local_torch_dtype": "float16",
  "local_quantization_mode": "none",
  "vllm_base_url": "http://localhost:8000/v1"
}
```

> `global_llm_api_key` は Fernet で暗号化して保存されます。空文字列 `""` を送ると既存キーを削除します。  
> `vllm_base_url` に値を設定するとローカル生成モデルが自動解放されます。空文字列 `""` で削除（ローカル AI モードに戻る）。  
> `local_torch_dtype` / `local_quantization_mode` を変更した後は `POST /api/admin/reload-generator` でモデルを再ロードしてください。

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

---

### `POST /api/admin/reload-generator`

ローカル AI テキスト生成モデル（generator）の再ロードを要求します。Bot が次回ポーリング時（最大 30 秒程度）に現在のモデルを破棄してバックグラウンドで再ロードします。モデルのサイズによっては再ロードに数分かかる場合があります。

**権限:** 要 Bot 管理者

**レスポンス:**
```json
{ "ok": true }
```

---

### `GET /api/admin/server-logs`

アプリケーションログファイルの末尾 N 行を返します。

**クエリパラメータ:**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `lines` | int | `200` | 取得する末尾行数（1〜5000） |

**レスポンス:**
```json
{
  "lines": [
    "2026-05-04 12:00:00 [INFO] src.main: Bot initialization is complete.",
    "2026-05-04 12:00:01 [WARNING] src.cogs.conv: ..."
  ],
  "log_file": "/data/ideal_bot.log",
  "available": true,
  "size_bytes": 204800
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `lines` | string[] | ログの末尾 N 行 |
| `log_file` | string | ログファイルのパス |
| `available` | boolean | `false` の場合はログファイル未設定またはファイルが存在しない |
| `size_bytes` | int | ログファイルの現在のサイズ（バイト） |

---

### `GET /api/admin/server-logs/download`

ログファイル全体をダウンロードします（`Content-Disposition: attachment` レスポンス）。

> `config.json` の `log_file` が設定されていない場合は `404` を返します。

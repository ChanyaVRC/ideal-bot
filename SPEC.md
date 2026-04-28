# ideal-bot 仕様書（実装準拠・2026-04-28）

## 概要

Discord サーバーで、登録語彙を使って応答する Bot。
現在の実装は以下を中核に構成される。

- Discord スラッシュコマンドによる語彙管理と設定変更
- チャンネル単位の会話モード
- 2系統の生成経路
  - 外部 LLM（OpenAI / Gemini）
  - ローカル生成（SentenceTransformers + transformers pipeline）
- FastAPI + React 管理画面（Discord OAuth2 + セッション認証）
- SQLite 永続化（マイグレーション管理）

---

## 1. 語彙登録

### 1.1 `/teach`

現在の実装は会話形式ではなく、引数指定形式。

- `/teach word:<単語> category:<カテゴリ>`
- カテゴリは autocomplete 対応（ギルド内既存カテゴリ）
- 重複（同一 reading キー）時は確認 UI を表示し、承認時に上書き
- 登録可否は許可リストで判定（空なら全員許可）

### 1.2 正規化

`config.category_normalization` で切替。

- `reading`: 読み仮名キーで管理
- `word`: 表記そのまま
- `vector`: カテゴリのみ類似判定で既存カテゴリへ寄せる（閾値 0.85）

### 1.3 権限管理（許可リスト）

- `/config teach_allow role:@role`
- `/config teach_allow user:@user`
- `/config teach_allow`（引数なし）: 許可リストをクリアして全員許可に戻す
- `/config teach_deny role:@role`
- `/config teach_deny user:@user`
- `/config teach_list`

`teach_list` はロール一覧 / ユーザー一覧の切替付き Embed を表示。

---

## 2. 発言トリガーと会話モード

### 2.1 発言トリガー

Bot は次の条件で返信する。

- メンションされたとき
- 会話モード中（pause 中を除く）
- 反応確率判定（`reply_rate`）に当たったとき

`reply_rate=0` の場合も、メンションと会話モード中の返信は継続する。

### 2.2 会話モード

- 単位: チャンネル
- TTL: `guild_settings.conversation_ttl`（分）
- 応答中の同チャンネル新規メッセージは個別返信せず、次ターン以降のコンテキストに含まれる
- 状態管理は `BotState` が保持（active/paused/processing/lock）

### 2.3 会話モード制御コマンド

- `/conv stop`
- `/conv pause minutes:<1-1440>`
- `/conv status`

日時処理は UTC aware (`datetime.now(UTC)`) で統一。

### 2.4 応答遅延

1. 読み取り遅延: `random.uniform(read_min, read_max)`
2. typing 表示
3. 生成
4. 入力遅延: `len(response) / type_cps` を 1.0〜8.0 秒にクランプ

遅延パラメータはギルド設定値があれば優先し、なければ `config.json` のデフォルトを使う。

---

## 3. 応答生成

## 3.1 生成経路の優先順位

1. ギルド or グローバル API キーがあれば LLM 経路
2. 失敗時はローカル経路へフォールバック
3. ローカル語彙ゼロ時は fallback 応答を返す

### 3.2 LLM 経路

- プロバイダ: `openai` / `gemini`
- モデル: 文字列で設定（固定リスト + 自由入力運用）
- コンテキスト: `conversation_log` の直近 `context_count` 件
- システム文: bot名、語彙リスト、persona、テーマ、長さ目安を注入

### 3.3 ローカル経路

- `SentenceTransformer` で語彙選択（上位 5語）
- 生成モデル設定時は `transformers` の `text-generation` pipeline を使用
- チャットテンプレート対応モデルでは multi-turn `context_history` を組み立てて生成
- `local_system_prompt` テンプレートを使用（変数: `{bot_name}`, `{length_hint}`）
- 設定不正時はデフォルトシステムプロンプトへフォールバック

### 3.4 ログ記録

Bot 応答時に以下を `conversation_log` へ保存。

- `reply_context`: `context_override` 指定時はユーザー発言のみ、それ以外はbot発言を含む全メッセージを `user:`/`assistant:` ラベル付きで記録
- `generation_metadata`（生成出力辞書 JSON）

---

## 4. Web 管理画面

### 4.1 認証方式

- Discord OAuth2
- FastAPI セッション（`ideal_bot_session`, HttpOnly, SameSite=Lax）
- 管理対象ギルドは Discord API + キャッシュで判定

### 4.2 画面構成（実装済み）

- `LoginPage`: Discord ログイン導線
- `GuildSelectPage`: 管理可能ギルド一覧
- `GuildDashboardPage`: 単語一覧 / ギルド設定
- `BotAdminPage`: グローバル設定、ギルド有効化、会話ログ、fallback 応答、コマンド再同期

### 4.3 Bot 管理者設定（実装）

- グローバル LLM provider/model/api key
- Discord キャッシュ TTL
- ローカルシステムプロンプト (`local_system_prompt`)
- slash command 再同期要求

### 4.4 `/dashboard` コマンド

- 現在は DM ではなく、実行チャンネルに URL を返す
- URL 形式: `{web_url}/guild/{guild_id}`

---

## 5. API 構成

### 5.1 主要ルーター

- `/auth/*`
  - login / callback / logout / me / guilds / bot
- `/api/guilds/*`
  - settings 取得更新、words 一覧削除
- `/api/admin/*`（Bot 管理者のみ）
  - settings、guilds、logs、fallback-responses、sync-commands

### 5.2 権限制御

- `require_auth`
- `require_bot_admin`
- `guild_access`

---

## 6. データ設計（SQLite）

### 6.1 テーブル

- `words`
- `guild_settings`
- `teach_allowlist`
- `conversation_log`
- `bot_settings`
- `fallback_responses`
- `discord_guild_cache`

### 6.2 `conversation_log` カラム

- 初期: `id, guild_id, channel_id, author_id, content, is_bot, created_at`
- v3 追加: `reply_context`
- v4 追加: `generation_metadata`

### 6.3 マイグレーション

`src/db/migrations/v1.sql` から順に適用し、`PRAGMA user_version` で管理。

---

## 7. コマンド一覧（実装済み）

### 7.1 一般

- `/teach`
- `/forget`
- `/wordlist`
- `/speak`

### 7.2 管理

- `/dashboard`
- `/reset`
- `/conv stop`
- `/conv pause`
- `/conv status`
- `/config reply_rate`
- `/config bot`
- `/config delay`
- `/config teach_allow`
- `/config teach_deny`
- `/config teach_list`
- `/config apikey`
- `/config model`

---

## 8. 設定（`config.json`）

主要項目（実装反映済み）。

- `discord_token` (必須)
- `encryption_master_key` (必須)
- `category_normalization`
- `sentence_transformer_model`
- `local_generation_model`
- `cpu_only_mode`
- `delay_read_min`, `delay_read_max`, `delay_type_cps`
- `conversation_log_retention_days`
- `log_level`
- `db_path`
- `web_url`, `web_host`, `web_port`, `frontend_url`
- `discord_client_id`, `discord_client_secret`, `discord_redirect_uri`
- `session_secret`
- `bot_admin_ids`

`load_config` は JSONC 形式（`//` コメント、末尾カンマ）を受理し、環境変数上書きに対応する。

---

## 9. 技術スタック

- Python 3.11+
- discord.py v2
- aiosqlite
- FastAPI
- React + TypeScript + Vite
- sentence-transformers
- transformers
- openai / google-genai
- cryptography(Fernet)
- pykakasi
- uv

---

## 10. 補足（現行との差分整理）

本書は「将来案」ではなく、現行コードの実装挙動を優先して記述している。
特に以下は実装準拠に合わせて更新済み。

- `/teach` は会話フローではなく引数入力式
- `/dashboard` は DM 送信ではなくチャンネル返信
- ローカルシステムプロンプトの Bot 管理者設定（`local_generation_model` のランタイム設定は削除済み、`config.json` での静的設定のみ）
- `conversation_log` の `reply_context` / `generation_metadata`

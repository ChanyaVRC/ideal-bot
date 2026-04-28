# API エンドポイント 概要

ベース URL: `http://localhost:8000`（本番: `https://your-domain.com`）

**認証:** Discord OAuth2 セッション Cookie（`ideal_bot_session`、HttpOnly / SameSite=Lax）

## 権限レベル

| レベル | 説明 |
|--------|------|
| **公開** | 認証不要 |
| **要ログイン** | セッション Cookie が必要 |
| **要ギルド権限** | ログイン済み、かつ対象ギルドの MANAGE_GUILD 権限が必要 |
| **要 Bot 管理者** | `config.json` の `bot_admin_ids` に登録済みのユーザーのみ |

## エンドポイント一覧

### [認証 (`/auth/*`)](./api-auth)

| メソッド | パス | 権限 | 説明 |
|---------|------|------|------|
| `GET` | [/auth/login](./api-auth#get-authlogin) | 公開 | Discord OAuth2 フロー開始 |
| `GET` | [/auth/callback](./api-auth#get-authcallback) | 公開 | OAuth2 コールバック |
| `POST` | [/auth/logout](./api-auth#post-authlogout) | 公開 | ログアウト |
| `GET` | [/auth/me](./api-auth#get-authme) | 要ログイン | ログイン中ユーザー情報 |
| `GET` | [/auth/guilds](./api-auth#get-authguilds) | 要ログイン | 管理可能ギルド一覧 |
| `GET` | [/auth/bot](./api-auth#get-authbot) | 公開 | Bot 情報 |

### [ギルド (`/api/guilds/*`)](./api-guilds)

| メソッド | パス | 権限 | 説明 |
|---------|------|------|------|
| `GET` | [/api/guilds/{guild_id}/settings](./api-guilds#get-apiguildsguild_idsettings) | 要ギルド権限 | ギルド設定取得 |
| `PATCH` | [/api/guilds/{guild_id}/settings](./api-guilds#patch-apiguildsguild_idsettings) | 要ギルド権限 | ギルド設定更新 |
| `GET` | [/api/guilds/{guild_id}/words](./api-guilds#get-apiguildsguild_idwords) | 要ギルド権限 | 語彙一覧取得 |
| `DELETE` | [/api/guilds/{guild_id}/words/{reading}](./api-guilds#delete-apiguildsguild_idwordsreading) | 要ギルド権限 | 語彙削除 |

### [管理者 (`/api/admin/*`)](./api-admin)

| メソッド | パス | 権限 | 説明 |
|---------|------|------|------|
| `GET` | [/api/admin/settings](./api-admin#get-apiadminsettings) | 要 Bot 管理者 | グローバル設定取得 |
| `PATCH` | [/api/admin/settings](./api-admin#patch-apiadminsettings) | 要 Bot 管理者 | グローバル設定更新 |
| `GET` | [/api/admin/guilds](./api-admin#get-apiadminguilds) | 要 Bot 管理者 | 全ギルド一覧 |
| `PATCH` | [/api/admin/guilds/{guild_id}](./api-admin#patch-apiadminguildsguild_id) | 要 Bot 管理者 | ギルド有効/無効切替 |
| `GET` | [/api/admin/logs](./api-admin#get-apiadminlogs) | 要 Bot 管理者 | 会話ログ取得 |
| `GET` | [/api/admin/fallback-responses](./api-admin#get-apiadminfallback-responses) | 要 Bot 管理者 | フォールバック応答一覧 |
| `POST` | [/api/admin/fallback-responses](./api-admin#post-apiadminfallback-responses) | 要 Bot 管理者 | フォールバック応答追加 |
| `DELETE` | [/api/admin/fallback-responses/{id}](./api-admin#delete-apiadminfallback-responsesresponse_id) | 要 Bot 管理者 | フォールバック応答削除 |
| `POST` | [/api/admin/sync-commands](./api-admin#post-apiadminsync-commands) | 要 Bot 管理者 | スラッシュコマンド再同期 |
| `POST` | [/api/admin/reload-generator](./api-admin#post-apiadminreload-generator) | 要 Bot 管理者 | ローカル AI 生成モデル再ロード |

## エラーレスポンス

| ステータス | 説明 |
|-----------|------|
| `400` | リクエスト不正（パラメータ欠落など） |
| `401` | 未認証（セッションなし） |
| `403` | 権限不足（ギルド管理権限なし / Bot 管理者でない） |
| `404` | リソースが見つからない |
| `502` | Discord API への接続失敗 |

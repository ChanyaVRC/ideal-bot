# 認証エンドポイント (`/auth/*`)

[← API 概要](./api)

---

### `GET /auth/login`

Discord OAuth2 認証フローを開始します。Discord の認可ページへリダイレクトします。

**権限:** 公開  
**レスポンス:** `307 Temporary Redirect`

---

### `GET /auth/callback`

Discord OAuth2 コールバック。トークン交換・セッション発行後にフロントエンドへリダイレクトします。

**権限:** 公開

**クエリパラメータ:**

| パラメータ | 必須 | 説明 |
|-----------|------|------|
| `code` | ○ | Discord から受け取った認可コード |
| `state` | ○ | CSRF 対策のステートトークン |
| `error` | — | エラー時に Discord から付与される |
| `guild` | — | ログイン後にリダイレクトするギルド ID |

**レスポンス:** `302 Redirect` → `/guilds` または `/guild/{guild_id}`

---

### `POST /auth/logout`

セッションをクリアしてログアウトします。

**権限:** 公開  
**レスポンス:**
```json
{ "ok": true }
```

---

### `GET /auth/me`

ログイン中のユーザー情報を返します。

**権限:** 要ログイン  
**レスポンス:**
```json
{
  "user_id": "123456789",
  "username": "Alice",
  "avatar": "avatar_hash",
  "managed_guilds": ["111111111111111111"],
  "is_bot_admin": false,
  "bot_name": "ideal-bot",
  "bot_avatar": "bot_avatar_hash"
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `user_id` | string | Discord ユーザー ID |
| `username` | string | 表示名 |
| `avatar` | string \| null | アバターハッシュ |
| `managed_guilds` | string[] | 管理権限を持つギルド ID のリスト |
| `is_bot_admin` | boolean | Bot 管理者かどうか |
| `bot_name` | string \| null | Bot のユーザー名 |
| `bot_avatar` | string \| null | Bot のアバターハッシュ |

---

### `GET /auth/guilds`

ログインユーザーが管理できる、かつ Bot が参加しているギルド一覧を返します。TTL 付きキャッシュを使用します（TTL は `discord_cache_ttl` 設定値）。

**権限:** 要ログイン  
**レスポンス:**
```json
[
  {
    "id": "111111111111111111",
    "name": "My Server",
    "icon": "icon_hash",
    "has_manage_guild": true
  }
]
```

---

### `GET /auth/bot`

Bot のユーザー名とアバターを返します。

**権限:** 公開  
**レスポンス:**
```json
{ "name": "ideal-bot", "avatar": "avatar_hash" }
```

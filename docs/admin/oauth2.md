# Discord OAuth2 設定

Web 管理画面の認証に Discord OAuth2 を使用します。

## 1. OAuth2 アプリの設定

1. [Discord Developer Portal](https://discord.com/developers/applications) を開く
2. ideal-bot のアプリケーションを選択
3. 左メニューから **OAuth2** を選択

## 2. リダイレクト URI の登録

**Redirects** セクションに、使用する環境の URI を追加します。

| 環境 | URI |
|------|-----|
| ローカル開発 | `http://localhost:8000/auth/callback` |
| 本番（Docker / systemd） | `https://your-domain.com/auth/callback` |

「Save Changes」をクリックして保存します。

> `config.json` の `web_url` を設定すれば、リダイレクト URI は自動導出されます（`web_url + "/auth/callback"`）。  
> Discord Developer Portal の登録値と一致させてください。

## 3. クライアント ID・シークレットの取得

**OAuth2 > General** ページで以下を確認します:

- **CLIENT ID** → `config.json` の `discord_client_id` に設定
- **CLIENT SECRET** → 「Reset Secret」で生成 → `discord_client_secret` に設定

## 4. Bot の作成とトークン設定

1. 左メニューから **Bot** を選択
2. Bot が未作成なら **Add Bot** をクリック
3. **TOKEN** を生成して `config.json` の `discord_token` に設定

> Bot トークンは絶対に公開しないでください。漏えいした場合は Developer Portal で再生成してください。

### Privileged Gateway Intents

本プロジェクトではメッセージ本文を扱うため、**MESSAGE CONTENT INTENT** を有効化してください。

## 5. Bot 招待リンク（初回のみ）

OAuth2 URL Generator で以下を選択して招待リンクを作成します。

- Scopes: `bot`, `applications.commands`
- Bot Permissions（現状の最小構成）:
  - `View Channels`
  - `Send Messages`

> 管理者向けコマンドの実行可否は、Bot 権限ではなく「実行ユーザーがサーバーで `Manage Server` を持つか」で判定されます。
> 将来、スレッド対応やメディア送信を追加した場合は `Send Messages in Threads` や `Embed Links` などを追加してください。

生成したリンクで対象サーバーに Bot を招待してください。

## 6. config.json の設定

```json
{
  "web_url": "https://your-domain.com",
  "discord_client_id": "1234567890123456789",
  "discord_client_secret": "abc123...",
  "session_secret": "ランダムな長い文字列",
  "bot_admin_ids": ["あなたのDiscordユーザーID"]
}
```

> `web_url` から `discord_redirect_uri`（`web_url + "/auth/callback"`）と `frontend_url` が自動導出されるため、個別指定は不要です。  
> ローカル開発時は `"web_url": "http://localhost:8000"` のままで動作します。

### セッションシークレットの生成

```bash
# ローカル
uv run python -c "import secrets; print(secrets.token_hex(32))"

# Docker（uv 未インストールの場合）
docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_hex(32))"
```

### Discord ユーザー ID の確認方法

1. Discord の設定 → 「詳細設定」→「開発者モード」をオン
2. 自分のプロフィールを右クリック → 「ユーザー ID をコピー」

## 7. 動作確認

### Docker を使っている場合

```bash
docker compose up -d
```

ブラウザで `https://your-domain.com/auth/login` を開き、Discord ログインが起動すれば設定完了です。

### ローカル環境の場合

```bash
./scripts/start-api.sh
```

ブラウザで `http://localhost:8000/auth/login` を開き、Discord ログインが起動すれば設定完了です。


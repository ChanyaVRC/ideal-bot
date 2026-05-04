# VPS へのデプロイ

デプロイ方式は 2 通りあります。

| 方式 | 向いているケース |
|------|----------------|
| [Docker（推奨）](#docker-を使ったデプロイ推奨) | 依存環境を揃えたい・本番運用 |
| [systemd](#systemd-を使ったデプロイdocker-を使わない場合) | Docker を使いたくない・既存サーバーへの追加 |

---

## Docker を使ったデプロイ（推奨）

### 前提条件

- Docker 24 以上
- Docker Compose v2 以上

### 初回セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/your-user/ideal-bot.git
cd ideal-bot

# 設定ファイルを作成
cp config.json.template config.json
```

`config.json` を編集します。

```json
{
  "discord_token": "YOUR_BOT_TOKEN",
  "encryption_master_key": "YOUR_FERNET_KEY",
  "web_url": "https://your-domain.com",
  "discord_client_id": "...",
  "discord_client_secret": "...",
  "session_secret": "...",
  "bot_admin_ids": ["123456789"]
}
```

> `db_path` と `log_file` は Dockerfile の ENV（`/data/ideal_bot.db`・`/data/ideal_bot.log`）が自動的に設定されるため記載不要です。  
> `discord_redirect_uri` / `frontend_url` は `web_url` から自動導出されます。

```bash
# ビルド & バックグラウンド起動
docker compose up --build -d

# ログ確認
docker compose logs -f
```

`config.json` をホスト側で編集後、`docker compose restart` のみで設定を反映できます。

### データディレクトリ

デフォルトではリポジトリ直下に `./data/` ディレクトリが自動作成され、以下のファイルが生成されます。

| ファイル | 内容 |
|---------|------|
| `./data/ideal_bot.db` | SQLite データベース |
| `./data/ideal_bot.log` | アプリケーションログ |

パスを変えたい場合は `DATA_DIR` 環境変数で上書きできます。

```bash
DATA_DIR=/opt/botdata docker compose up -d
```

`hf_cache`（HuggingFace モデルキャッシュ）は Docker 管理の名前付きボリュームとして保持されます。

### ログの確認

ホストから直接ログをテールできます。

```bash
tail -f ./data/ideal_bot.log
```

Web 管理画面の **Bot 管理者 → サーバーログ** タブでも、最新ログの閲覧・レベル絞り込み・ダウンロードができます。

### nginx リバースプロキシ

`web_url` には nginx 側のドメイン（公開 URL）を設定してください。FastAPI は内部で `0.0.0.0:8000` のまま動作します。

```
[ブラウザ] → https://your-domain.com (nginx :443) → http://127.0.0.1:8000 (Docker FastAPI)
              ↑ web_url に書く値                     ↑ nginx の proxy_pass
```

```nginx
# /etc/nginx/sites-available/ideal-bot
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/ideal-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**Let's Encrypt で証明書を取得する場合：**

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

certbot が nginx 設定を自動更新します。その後 `docker compose up -d` で起動してください。

---

## systemd を使ったデプロイ（Docker を使わない場合）

### 前提条件

- VPS（Ubuntu 22.04 推奨）
- Python 3.11 以上
- Node.js 20 以上
- uv インストール済み
- nginx（リバースプロキシ用）

### 初回セットアップ

```bash
# VPS にリポジトリをクローン
sudo mkdir -p /opt/ideal-bot
sudo chown $USER:$USER /opt/ideal-bot
git clone https://github.com/your-user/ideal-bot.git /opt/ideal-bot
cd /opt/ideal-bot

# 設定ファイルを作成・編集
cp config.json.template config.json

# Python 依存関係
uv sync --extra web

# フロントエンドビルド
cd frontend && npm ci && npm run build && cd ..
```

### systemd サービスの設定

```bash
sudo nano /etc/systemd/system/ideal-bot.service
```

```ini
[Unit]
Description=ideal-bot Discord Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ideal-bot
ExecStart=/opt/ideal-bot/scripts/start-bot.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo nano /etc/systemd/system/ideal-bot-api.service
```

```ini
[Unit]
Description=ideal-bot Web API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ideal-bot
ExecStart=/opt/ideal-bot/scripts/start-api.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ideal-bot ideal-bot-api
sudo systemctl start ideal-bot ideal-bot-api

# 状態確認
sudo systemctl status ideal-bot ideal-bot-api
```

### nginx の設定

```nginx
# /etc/nginx/sites-available/ideal-bot
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # API・OAuth2 エンドポイント（FastAPI に転送）
    location /api/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    location /auth/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    # React フロントエンド（静的ファイル）
    location / {
        root       /opt/ideal-bot/frontend/dist;
        try_files  $uri $uri/ /index.html;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/ideal-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**Let's Encrypt で証明書を取得する場合：**

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

certbot が `ssl_certificate` などの行を自動補完します。

### ログの確認

```bash
# Bot ログ
sudo journalctl -u ideal-bot -f

# API ログ
sudo journalctl -u ideal-bot-api -f
```

---

## GitHub Actions による自動デプロイ（共通）

`main` ブランチへの push で自動的にテスト → デプロイが実行されます。

### Secrets の設定

**Settings > Secrets and variables > Actions > Secrets** に以下を登録してください:

| シークレット名 | 説明 |
|-------------|------|
| `VPS_HOST` | VPS のホスト名または IP |
| `VPS_USER` | SSH ユーザー名 |
| `VPS_SSH_KEY` | SSH 秘密鍵（`cat ~/.ssh/id_ed25519`） |
| `VPS_PORT` | SSH ポート（デフォルト: 22） |

### デプロイモードの切り替え

**Settings > Secrets and variables > Actions > Variables** に以下を登録してください:

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `DEPLOY_MODE` | `docker`（デフォルト）または `systemd` | デプロイ方式の選択 |

- `docker`: VPS で `./scripts/update.sh --docker` を実行（Docker Compose 再ビルド）
- `systemd`: VPS で `./scripts/update.sh` を実行してから `systemctl restart`


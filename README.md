# ideal-bot

Discord サーバー上で「教えられた単語・フレーズ」を使って自然に発言する Bot。  
サーバーごとに語彙・設定を管理し、LLM 連携・ローカル AI・Web 管理画面を備えた本格的な構成です。

## 特徴

- **語彙登録** — `/teach` コマンドで単語をインタラクティブに登録
- **自然な発言** — ローカル AI（SentenceTransformers + transformers pipeline）・OpenAI/Gemini LLM・vLLM（OpenAI 互換の自前推論サーバー）で発言生成
- **会話モード** — メンション or 反応発言をトリガーに、チャンネルへ継続参加
- **Web 管理画面** — Discord OAuth2 認証付き React 管理 UI（Bot 管理者・サーバー管理者の 2 階層）
- **サーバーログビューアー** — 管理画面からログをリアルタイム閲覧・レベル絞り込み・ダウンロード
- **サーバー分離** — ギルドごとに語彙・設定・LLM API キーを完全分離
- **応答遅延** — 「読んでいる」「タイピングしている」感を再現する遅延機構

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| Discord Bot | Python 3.11+, discord.py v2 |
| AI / LLM | sentence-transformers, transformers, OpenAI, Google Gemini, vLLM |
| DB | SQLite (aiosqlite) |
| Web API | FastAPI, Starlette SessionMiddleware |
| Web UI | React 18, TypeScript, Vite, shadcn/ui, Zustand |
| パッケージ管理 | uv |
| コンテナ | Docker / Docker Compose |

## 必要環境

- Python 3.11 以上
- [uv](https://docs.astral.sh/uv/) パッケージマネージャー
- Node.js 20 以上（Web 管理画面を使う場合）
- Linux / macOS（本番は Linux VPS 推奨）

## クイックスタート

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-user/ideal-bot.git
cd ideal-bot
```

### 2. 設定ファイルの準備

```bash
cp config.json.template config.json
```

`config.json` を編集して最低限の設定を行います。

```json
{
  "discord_token": "YOUR_BOT_TOKEN",
  "encryption_master_key": "YOUR_FERNET_KEY"
}
```

Fernet キーの生成方法：

```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. 依存関係のインストール

```bash
# Bot のみ
uv sync

# Web 管理画面も使う場合
uv sync --extra web
```

### 4. Bot の起動

```bash
# Bot のみ
./scripts/start-bot.sh

# Web API のみ
./scripts/start-api.sh

# 両方
./scripts/start-all.sh
```

### 5. Web 管理画面のセットアップ（任意）

```bash
cd frontend
npm install
npm run dev   # 開発サーバー（http://localhost:5173）
```

本番ビルド：

```bash
cd frontend && npm run build
# ビルド成果物 frontend/dist/ が FastAPI から静的ファイルとして配信されます
```

## ディレクトリ構成

```
ideal-bot/
├── src/
│   ├── main.py          # Discord Bot エントリーポイント
│   ├── config.py        # 設定管理
│   ├── state.py         # Bot ランタイム状態
│   ├── ai/              # ローカル AI (SentenceTransformers)
│   ├── cogs/            # Discord コグ（コマンド実装）
│   ├── db/              # SQLite アクセス層
│   ├── utils/           # ユーティリティ
│   ├── views/           # Discord UI コンポーネント
│   └── api/             # FastAPI Web バックエンド
│       ├── app.py
│       ├── auth.py      # Discord OAuth2
│       ├── deps.py      # 依存関係注入
│       ├── models.py    # Pydantic モデル
│       └── routers/     # API ルーター
├── frontend/            # React Web 管理画面
│   └── src/
│       ├── api/         # API クライアント
│       ├── components/  # UI コンポーネント
│       ├── pages/       # ページコンポーネント
│       └── store/       # Zustand ストア
├── tests/               # pytest テスト
├── docs/                # VitePress ドキュメント
├── scripts/             # 起動スクリプト
└── config.json.template # 設定テンプレート
```

## 設定リファレンス

主要な設定項目（`config.json`）：

| キー | 説明 | デフォルト |
|------|------|----------|
| `discord_token` | Discord Bot トークン | 必須 |
| `encryption_master_key` | LLM API キー暗号化用 Fernet キー | 必須 |
| `discord_client_id` | Discord OAuth2 クライアント ID | Web 管理画面使用時は必須 |
| `discord_client_secret` | Discord OAuth2 クライアントシークレット | Web 管理画面使用時は必須 |
| `session_secret` | セッション署名キー | Web 管理画面使用時は必須 |
| `bot_admin_ids` | Bot 管理者の Discord ユーザー ID リスト | `[]` |
| `sentence_transformer_model` | SentenceTransformers モデル名 | `paraphrase-multilingual-MiniLM-L12-v2` |
| `web_host` | API サーバーのバインドアドレス | `0.0.0.0` |
| `web_port` | API サーバーのポート | `8000` |
| `frontend_url` | フロントエンドの URL（CORS 設定用） | `http://localhost:5173` |

詳細は [ドキュメント](https://your-user.github.io/ideal-bot/) を参照してください。

## ボットコマンド

| コマンド | 説明 | 権限 |
|---------|------|------|
| `/teach` | 単語を登録 | 設定による |
| `/forget <単語>` | 単語を削除 | 登録者 or 管理者 |
| `/wordlist [category]` | 登録単語一覧 | 全員 |
| `/speak [category] [theme]` | 強制発言 | 全員 |
| `/dashboard` | 管理画面 URL を DM で送信 | 管理者 |
| `/config reply_rate <0-100>` | 反応確率を設定 | 管理者 |
| `/config bot <on\|off>` | Bot の反応を有効/無効 | 管理者 |
| `/conv stop` | 会話モードを即時終了 | 管理者 |
| `/reset` | 全単語をリセット | 管理者 |

## テスト

```bash
# Python テスト（Bot + API）
uv sync --extra web --group dev
uv run pytest tests/ -v

# フロントエンドテスト
cd frontend
npm install
npm test
```

## Docker で起動する

### 1. 設定ファイルを用意

```bash
cp config.json.template config.json
```

`config.json` を編集して必要な値を設定します。

```json
{
  "discord_token": "YOUR_BOT_TOKEN",
  "encryption_master_key": "YOUR_FERNET_KEY",
  "web_url": "http://your-domain.com",
  "discord_client_id": "...",
  "discord_client_secret": "...",
  "session_secret": "...",
  "bot_admin_ids": ["123456789"]
}
```

> `db_path`・`log_file` は Dockerfile の ENV が自動的に `/data/ideal_bot.db`・`/data/ideal_bot.log` を設定するため記載不要です。

### 2. ビルド & 起動

```bash
docker compose up --build -d
```

- API + Web UI: `http://localhost:8000`
- DB とログは `./data/` ディレクトリに出力されます（初回起動時に自動作成）
- HuggingFace モデルキャッシュは Docker 名前付きボリュームで管理されます

### 3. 設定変更

ホストの `config.json` を編集してコンテナを再起動するだけです。

```bash
# config.json を編集後
docker compose restart
```

### 4. ログ確認

```bash
# Docker コンテナの標準出力ログ
docker compose logs -f

# アプリケーションログファイル（ホストから直接参照可）
tail -f ./data/ideal_bot.log
```

Web 管理画面の **Bot 管理者 → サーバーログ** タブでも閲覧・ダウンロードできます。

### 5. 停止

```bash
docker compose down
```

---

## 本番デプロイ

### systemd サービス例

```ini
# /etc/systemd/system/ideal-bot.service
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

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/ideal-bot-api.service
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

[Install]
WantedBy=multi-user.target
```

### nginx リバースプロキシ例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /auth/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        root /opt/ideal-bot/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

## ライセンス

MIT

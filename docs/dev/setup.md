# 開発環境のセットアップ

## 前提条件

- Python 3.11 以上
- [uv](https://docs.astral.sh/uv/) 0.4 以上
- Node.js 20 以上
- Git

## リポジトリのクローンと初期設定

```bash
git clone https://github.com/your-user/ideal-bot.git
cd ideal-bot

# セットアップスクリプトを実行（config.json 作成・依存関係インストールを一括で行います）
./scripts/setup.sh
```

スクリプトは以下を自動で行います：

- Discord Bot トークン・OAuth2 クライアント ID/シークレット・管理者 ID を対話入力
- `encryption_master_key` と `session_secret` をランダム生成して `config.json` に書き込み
- Python 依存関係（`uv sync --extra web --group dev`）のインストール
- フロントエンド依存関係（`npm install`）のインストール

Bot トークンをコマンドライン引数で渡すこともできます：

```bash
./scripts/setup.sh --token YOUR_BOT_TOKEN
```

セットアップ完了後、`config.json` を開いて未入力の項目（`web_url` など）を確認してください。

## テストの実行

```bash
# Python テスト（Bot + API）
uv run pytest tests/ -v

# フロントエンドテスト
cd frontend && npm test

# フロントエンド型チェック
cd frontend && npm run typecheck
```

## 開発サーバーの起動

```bash
# Bot（ターミナル 1）
./scripts/start-bot.sh

# API サーバー（ターミナル 2）
./scripts/start-api.sh --reload

# フロントエンド開発サーバー（ターミナル 3）
cd frontend && npm run dev
```

## ドキュメントの開発

```bash
cd docs
npm install
npm run dev  # http://localhost:5173 で起動
```

## プロジェクト構成

```
ideal-bot/
├── src/
│   ├── main.py          # Discord Bot エントリーポイント
│   ├── config.py        # 設定管理（dataclass）
│   ├── state.py         # Bot ランタイム状態
│   ├── ai/              # ローカル AI
│   │   └── local.py     # SentenceTransformers
│   ├── cogs/            # Discord コグ
│   │   ├── teach.py     # /teach コマンド
│   │   ├── events.py    # メッセージイベント
│   │   ├── conv.py      # /conv コマンド
│   │   └── ...
│   ├── db/              # SQLite アクセス層
│   │   ├── connection.py
│   │   ├── words.py
│   │   ├── guild_settings.py
│   │   └── ...
│   └── api/             # FastAPI バックエンド
│       ├── app.py       # アプリファクトリ
│       ├── auth.py      # Discord OAuth2
│       ├── deps.py      # 依存関係注入
│       ├── models.py    # Pydantic モデル
│       └── routers/
├── frontend/            # React 管理画面
├── tests/               # pytest テスト
├── docs/                # このドキュメント
├── scripts/             # 起動スクリプト
└── pyproject.toml
```

## コーディング規約

- Python: `ruff` フォーマット（`uv run ruff format .`）
- TypeScript: Vite + TypeScript strict mode
- テスト: pytest (asyncio_mode=auto), Vitest

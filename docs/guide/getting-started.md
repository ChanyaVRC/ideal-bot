# セットアップ

セットアップ方法は 2 通りあります。

| 方法 | 向いているケース |
|------|----------------|
| [Docker（推奨）](#docker-を使ったセットアップ推奨) | 本番環境・手軽に試したい |
| [ローカル](#ローカル環境でのセットアップ) | 開発・カスタマイズ |

---

## Docker を使ったセットアップ（推奨）

### 必要環境

- **Docker 24 以上**
- **Docker Compose v2 以上**

### 手順

#### 1. リポジトリのクローン

```bash
git clone https://github.com/your-user/ideal-bot.git
cd ideal-bot
```

#### 2. 設定ファイルの準備

```bash
cp config.json.template config.json
```

`config.json` を開き、最低限必要な項目を設定します。

```json
{
  "discord_token": "YOUR_BOT_TOKEN",
  "encryption_master_key": "YOUR_FERNET_KEY"
}
```

**Fernet キーの生成：**

```bash
docker run --rm python:3.12-slim python -c \
  "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Web 管理画面も使う場合は追加で設定が必要です。詳細は [設定リファレンス](./config.md) を参照してください。

#### 3. Discord Bot の作成

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリを作成
2. **Bot** タブでトークンを発行 → `discord_token` に設定
3. **Bot** タブで **MESSAGE CONTENT INTENT** を有効化
4. **OAuth2 > URL Generator** でスコープ `bot` + `applications.commands` を選択して招待リンクを生成

#### 4. ビルドと起動

```bash
docker compose up --build -d
```

ログの確認：

```bash
docker compose logs -f
```

#### 5. 動作確認

Discord サーバーに Bot を招待し、`/teach` コマンドを試してみてください。

#### 停止・再起動

```bash
# 停止
docker compose down

# 設定変更後の再起動（ビルド不要）
docker compose restart

# イメージから再ビルドして起動
docker compose up --build -d
```

---

## ローカル環境でのセットアップ

### 必要環境

- **Python 3.11 以上**
- **[uv](https://docs.astral.sh/uv/)** — Python パッケージマネージャー
- **Node.js 20 以上**（Web 管理画面を使う場合）
- **Linux / macOS**（本番は Linux VPS 推奨）

### 手順

#### 1. リポジトリのクローン

```bash
git clone https://github.com/your-user/ideal-bot.git
cd ideal-bot
```

#### 2. セットアップスクリプトの実行

```bash
./scripts/setup.sh
```

スクリプトが対話形式で設定値を入力し、`config.json` 作成・依存関係インストールまで一括で行います。  
Bot トークンを引数で渡すこともできます：

```bash
./scripts/setup.sh --token YOUR_BOT_TOKEN
```

#### 3. Discord Bot の作成

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリを作成
2. **Bot** タブでトークンを発行 → `discord_token` に設定
3. **Bot** タブで **MESSAGE CONTENT INTENT** を有効化
4. **OAuth2 > URL Generator** でスコープ `bot` + `applications.commands` を選択して招待リンクを生成

#### 4. Bot の起動

```bash
# Discord Bot を起動
./scripts/start-bot.sh

# Web API サーバーを起動（別ターミナル）
./scripts/start-api.sh

# または両方を同時に起動
./scripts/start-all.sh
```

#### 5. フロントエンドの起動（開発）

```bash
cd frontend
npm run dev  # http://localhost:5173 で起動
```

#### 6. 動作確認

Discord サーバーに Bot を招待し、`/teach` コマンドを試してみてください。

---

## 次のステップ

- [設定リファレンス](./config.md) — `config.json` の全設定項目
- [コマンド一覧](./commands.md) — 利用できるスラッシュコマンド
- [Web 管理画面](../admin/overview.md) — ブラウザからの管理
- [アップデート](./update.md) — Bot を最新バージョンに更新する方法

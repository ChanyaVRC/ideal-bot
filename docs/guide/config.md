# 設定リファレンス

設定は `config.json` で管理します。リポジトリには `config.json.template`（値を空にしたテンプレート）を同梱しています。

```bash
cp config.json.template config.json
# config.json を編集
```

::: warning
`config.json` は `.gitignore` に含まれているため、Git でバージョン管理されません。機密情報を安全に保管してください。
:::

## 必須項目

| キー | 説明 |
|------|------|
| `discord_token` | Discord Bot トークン |
| `encryption_master_key` | LLM API キー暗号化用の Fernet キー |

## Bot 動作設定

| キー | 説明 | デフォルト |
|------|------|----------|
| `db_path` | SQLite データベースのパス | `ideal_bot.db` |
| `category_normalization` | カテゴリ正規化方式 (`reading` / `vector`) | `reading` |
| `sentence_transformer_model` | SentenceTransformers モデル名 | `paraphrase-multilingual-MiniLM-L12-v2` |
| `delay_read_min` | 読み取り遅延の最小秒数 | `10` |
| `delay_read_max` | 読み取り遅延の最大秒数 | `30` |
| `delay_type_cps` | タイピング速度（文字/秒） | `5` |
| `conversation_log_retention_days` | 会話ログの保持日数 | `7` |

## ログ設定

| キー | 説明 | デフォルト |
|------|------|----------|
| `log_file` | ログファイルのパス。空文字の場合はファイル出力なし | `""` |
| `log_level` | ログレベル (`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`) | `INFO` |
| `log_max_bytes` | ログファイルの最大サイズ（バイト）。超えると自動ローテーション | `10485760`（10 MB）|
| `log_backup_count` | ローテーション後の保持世代数 | `3` |

ログファイルを設定すると、Web 管理画面の **Bot 管理者 → サーバーログ** タブでリアルタイム閲覧・ダウンロードができます。

> Docker 環境では `LOG_FILE` 環境変数が自動的に `/data/ideal_bot.log` を設定します（`config.json` の `log_file` より優先）。  
> ログは `./data/ideal_bot.log` としてホストから直接参照できます。

## Web 管理画面設定

| キー | 説明 | デフォルト |
|------|------|----------|
| `web_url` | 管理画面の公開 URL。`discord_redirect_uri` と `frontend_url` の導出に使われます | `http://localhost:8000` |
| `discord_client_id` | Discord OAuth2 クライアント ID | `""` |
| `discord_client_secret` | Discord OAuth2 クライアントシークレット | `""` |
| `discord_redirect_uri` | OAuth2 コールバック URI。省略時は `web_url + "/auth/callback"` | *(自動導出)* |
| `session_secret` | セッション署名キー（ランダムな長い文字列） | `""` |
| `bot_admin_ids` | Bot 管理者の Discord ユーザー ID のリスト | `[]` |
| `web_host` | API サーバーのバインドアドレス | `0.0.0.0` |
| `web_port` | API サーバーのポート番号 | `8000` |
| `frontend_url` | フロントエンドの URL（CORS 設定用）。省略時は `web_url` と同じ値 | *(自動導出)* |

> `web_host`・`web_port`・`discord_redirect_uri`・`frontend_url` は通常 `config.json` に記載不要です。  
> Docker 環境では `web_host`・`web_port`・`db_path` が Dockerfile の ENV で自動設定されます。

## サンプル config.json

```json
{
  "discord_token": "MTIz...（Botトークン）",
  "encryption_master_key": "abc123...（Fernetキー）",

  "db_path": "ideal_bot.db",
  "category_normalization": "reading",
  "sentence_transformer_model": "paraphrase-multilingual-MiniLM-L12-v2",

  "delay_read_min": 10,
  "delay_read_max": 30,
  "delay_type_cps": 5,
  "conversation_log_retention_days": 7,

  "discord_client_id": "1234567890",
  "discord_client_secret": "abc...（クライアントシークレット）",
  "web_url": "https://your-domain.com",
  "session_secret": "ランダムな長い文字列（32文字以上推奨）",
  "bot_admin_ids": ["あなたのDiscordユーザーID"]
}
```

## Fernet キーの生成

```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## カテゴリ正規化モード

`category_normalization` の設定値によりカテゴリの重複検出方式が変わります。

| モード | 説明 | 特徴 |
|--------|------|------|
| `reading` | pykakasi でひらがな読みに変換して比較 | 軽量・デフォルト |
| `word` | 表記そのままで比較（完全一致） | 厳密一致 |
| `vector` | SentenceTransformers で意味的類似度を比較（閾値: 0.85） | 高精度・重い |

**vector モードの動作：**  
`/teach` で新しいカテゴリを入力すると、既存カテゴリとのコサイン類似度を計算します。  
類似度が 0.85 以上のカテゴリが見つかった場合、入力されたカテゴリはその既存カテゴリに統合されます。  
例：「形容詞」登録済みの状態で「けいようし」と入力 → 自動的に「形容詞」として登録されます。

## SentenceTransformers モデル候補

| モデル名 | サイズ | 特徴 |
|---------|-------|------|
| `paraphrase-multilingual-MiniLM-L12-v2` | 118MB | 軽量・高速・**推奨** |
| `multilingual-e5-small` | 118MB | E5 系列・高精度 |
| `paraphrase-multilingual-mpnet-base-v2` | 278MB | より高精度 |
| `multilingual-e5-base` | 278MB | バランス型 |
| `cl-nagoya/sup-simcse-ja-base` | 111MB | 日本語専用・高精度 |

モデルは初回起動時に Hugging Face から自動ダウンロードされ、`~/.cache/huggingface/` にキャッシュされます。

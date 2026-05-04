# Web 管理画面

## 概要

ideal-bot には Discord OAuth2 認証付きの Web 管理画面があります。  
ギルド管理者はブラウザから語彙・設定・LLM キーを管理できます。

## 画面構成

### ログイン画面 (`/login`)

Discord アカウントでログインします。Bot が参加しているサーバーの管理権限（MANAGE_GUILD）を持つユーザーのみ操作できます。

### サーバー選択 (`/guilds`)

Bot が参加しているサーバーのうち、あなたが管理権限を持つサーバーの一覧を表示します。クリックで各サーバーの管理画面に進みます。

Bot 管理者には「Bot 管理者設定」ボタンも表示されます。

### サーバー管理画面 (`/guild/:guildId`)

**単語一覧タブ**
- 登録語彙の検索・確認・削除

**設定タブ**
- Bot 有効/無効
- 反応確率（reply_rate）
- 会話モード継続時間（conversation_ttl）
- 会話コンテキスト件数（context_count）
- 応答遅延パラメータ
- Bot のキャラクター・口調（bot_persona）
- LLM プロバイダー・モデル
- ギルド専用 LLM API キー

### Bot 管理者画面 (`/admin`)

**Bot 管理者のみアクセス可能**（`config.json` の `bot_admin_ids` に登録されたユーザー）

**グローバル設定タブ**
- Bot 全体の LLM API キー（ギルド専用キーがない場合のフォールバック）
- グローバル LLM プロバイダー・モデル
- vLLM エンドポイント URL（OpenAI 互換の自前推論サーバー用）
- Discord キャッシュ TTL
- ローカル LLM システムプロンプト
- スラッシュコマンドの再同期

**ギルド一覧タブ**
- 全ギルドの Bot 有効/無効を一覧管理

**サーバーログタブ**
- アプリケーションログのリアルタイム閲覧（末尾 N 行）
- ログレベル（ERROR / WARNING / INFO / DEBUG）ごとの表示/非表示フィルター
- 絞り込んだ状態でのファイルダウンロード

> ログを表示するには `config.json` の `log_file` にパスを設定する必要があります。  
> Docker 環境では `./data/ideal_bot.log` に自動出力されるため設定不要です。

## `/dashboard` コマンド

Discord サーバー内から管理画面の URL を受け取ることができます:

```
/dashboard
```

Bot が実行チャンネルに管理画面の URL（`https://your-domain.com/guild/ギルドID`）を返信します。  
未ログインの場合は Discord ログインページへ誘導されます。

## 認証の仕組み

```
1. ユーザーが管理画面にアクセス
2. Discord OAuth2 でログイン（スコープ: identify guilds）
3. FastAPI がセッション発行（httponly 署名付き Cookie）
4. セッションに「管理できるギルド一覧」を保持
5. 以降のリクエストはセッション Cookie で認証
```

JWT は使用せず、セキュアなセッション Cookie で管理しています。

## 次のステップ

- [Discord OAuth2 設定](./oauth2.md) — OAuth2 アプリの作成・設定方法

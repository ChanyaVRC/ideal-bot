# アップデート

## Docker を使っている場合

```bash
./scripts/update.sh --docker
```

内部で `git pull` → `docker compose up --build -d` を実行します。

データベースのマイグレーションはコンテナ起動時に自動実行されます。

---

## ローカル環境の場合

```bash
./scripts/update.sh
```

内部で `git pull` → `uv sync --extra web` → `npm install` を実行します。  
完了後にサービスを再起動してください。

```bash
./scripts/start-all.sh
```

データベースのマイグレーションは起動時に自動実行されます。

---

## config.json のマイグレーション

新しいバージョンで設定項目が追加された場合は、`config.json.template` と既存の `config.json` を比較して必要な項目を追記してください。

```bash
diff config.json.template config.json
```

既存の `config.json` に書かれていない項目はデフォルト値が使われるため、不要な項目は追加しなくても動作します。

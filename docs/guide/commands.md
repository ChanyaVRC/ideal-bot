# コマンド一覧

## 語彙管理

### `/teach` — 単語を登録

```
/teach
```

Bot が会話形式で単語とカテゴリを聞き出します。登録制限がある場合は許可されたユーザー・ロールのみ実行できます。

**フロー:**
```
Bot: 教えてくれる単語を入力してください（例: ふわふわ、どきどき）
User: ふわふわ
Bot: カテゴリを入力してください（例: 形容詞、感情、挨拶）
User: 形容詞
Bot: 「ふわふわ」を「形容詞」として登録しました！
```

重複する単語が既にある場合は確認ボタンを表示します。

---

### `/forget <単語>` — 単語を削除

```
/forget ふわふわ
```

登録者本人または管理者のみ削除できます。

---

### `/wordlist [category]` — 登録単語一覧

```
/wordlist
/wordlist category:形容詞
```

ページネーション付きの Embed でギルドの登録語彙を表示します。カテゴリを指定してフィルタリングもできます。

---

### `/reset` — 全単語をリセット

```
/reset
```

**管理者専用。** 確認ステップあり。ギルドの全登録語彙を削除します。

---

## 発言・会話

### `/speak [category] [theme]` — 強制発言

```
/speak
/speak category:形容詞
/speak theme:今日の天気
```

Bot を強制的に発言させます。

| オプション | 説明 |
|-----------|------|
| `category` | 指定カテゴリから語彙を選択（autocomplete 対応） |
| `theme` | テーマを指定（LLM あり: プロンプトに反映、LLM なし: 意味的に近い語彙を選択） |

---

### `/conv stop` — 会話モードを終了

```
/conv stop
```

**管理者専用。** そのチャンネルの会話モードを即時終了します。

---

### `/conv pause <分>` — 会話モードを一時停止

```
/conv pause 10
```

**管理者専用。** 指定した分数だけ会話モードを一時停止します。時間経過後に自動再開。

---

### `/conv status` — 会話モード状態確認

```
/conv status
```

**管理者専用。** アクティブな会話モードのチャンネル一覧と残り時間を表示します。

---

## 管理・設定

### `/config reply_rate <0-100>` — 反応確率を設定

```
/config reply_rate 20
```

**管理者専用。** Bot がメッセージに反応する確率（%）を設定します。`0` で反応発言なし（メンション・コマンドは引き続き動作）。

---

### `/config bot <on|off>` — Bot の反応を切り替え

```
/config bot off
/config bot on
```

**管理者専用。** このサーバーでの Bot の発言を有効/無効にします。

---

### `/config delay read_min <秒> read_max <秒> type_cps <文字/秒>` — 応答遅延を設定

```
/config delay read_min 1 read_max 3 type_cps 15
```

**管理者専用。** 応答遅延のパラメータを設定します。

| パラメータ | 説明 | デフォルト |
|-----------|------|----------|
| `read_min` | 読み取り遅延の最小秒数 | 1 |
| `read_max` | 読み取り遅延の最大秒数 | 3 |
| `type_cps` | タイピング速度（文字/秒） | 15 |

---

### `/config apikey <provider> <key>` — LLM API キーを登録

```
/config apikey openai sk-...
/config apikey gemini AI...
```

**管理者専用。** このギルド専用の LLM API キーを暗号化して保存します。

---

### `/config model <モデル名>` — LLM モデルを選択

```
/config model gpt-4o-mini
/config model gemini-2.0-flash
```

**管理者専用。** 使用する LLM モデルを選択します（autocomplete 対応）。

---

### `/config teach_allow <role|user> <対象>` — 登録許可リストに追加

```
/config teach_allow role:@モデレーター
/config teach_allow user:@username
/config teach_allow everyone
```

**管理者専用。** 単語登録を許可するロール/ユーザーを追加します。`everyone` で全員許可に戻します。

---

### `/config teach_deny <role|user> <対象>` — 許可リストから除外

```
/config teach_deny role:@ロール名
/config teach_deny user:@username
```

**管理者専用。**

---

### `/config teach_list` — 許可リストを表示

```
/config teach_list
```

**管理者専用。** 現在の登録許可ロール・ユーザー一覧を Embed で表示します（ページネーション付き）。

---

### `/dashboard` — 管理画面 URL を DM で送信

```
/dashboard
```

**管理者専用。** Web 管理画面の URL を DM で送信します。

---
layout: home

hero:
  name: ideal-bot
  text: 語彙で話す Discord Bot
  tagline: 教えられた言葉を使って自然に発言・会話する Discord Bot
  actions:
    - theme: brand
      text: セットアップ
      link: /guide/getting-started
    - theme: alt
      text: コマンド一覧
      link: /guide/commands

features:
  - icon: 📚
    title: 語彙登録
    details: /teach コマンドで単語を会話形式で登録。カテゴリ・読み仮名で整理し重複も自動検出します。

  - icon: 🤖
    title: ローカル AI / LLM 対応
    details: API キーなしでも SentenceTransformers によるローカル AI で発言生成。OpenAI・Gemini にも対応。

  - icon: 💬
    title: 会話モード
    details: メンションをトリガーにチャンネルへ継続参加。コンテキストを保持して自然な会話を実現します。

  - icon: 🖥️
    title: Web 管理画面
    details: Discord OAuth2 認証付きの React 管理 UI。語彙・設定・LLM キーをブラウザから管理できます。

  - icon: 🔒
    title: サーバー分離
    details: ギルドごとに語彙・設定・API キーを完全分離。複数サーバーで独立して動作します。

  - icon: ⚡
    title: uv で高速セットアップ
    details: Python パッケージ管理に uv を採用。依存解決・仮想環境管理が高速で再現性も高いです。
---

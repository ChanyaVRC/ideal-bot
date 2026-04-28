#!/usr/bin/env bash
# Initial setup script for ideal-bot.
# Checks prerequisites, installs dependencies, and prepares config.json.
set -euo pipefail

cd "$(dirname "$0")/.."

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC}    $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── 引数解析 ──────────────────────────────────────────────────────────────────

DISCORD_TOKEN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --token)
      [[ -z "${2:-}" ]] && { fail "--token の値が指定されていません"; }
      DISCORD_TOKEN="$2"
      shift 2
      ;;
    --token=*)
      DISCORD_TOKEN="${1#--token=}"
      shift
      ;;
    -h|--help)
      echo "使い方: $0 [--token <discord_token>]"
      echo ""
      echo "  --token <token>  Discord Bot トークンを引数で指定する（省略時は対話入力）"
      exit 0
      ;;
    *)
      fail "不明なオプション: $1"
      ;;
  esac
done

echo "=== ideal-bot セットアップ ==="
echo ""

# ── 前提条件チェック ──────────────────────────────────────────────────────────

echo "前提条件を確認しています..."

# Python 3.11+
if command -v python3 &>/dev/null; then
  PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
  PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
  if [[ "$PY_MAJOR" -lt 3 || ( "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 11 ) ]]; then
    fail "Python 3.11 以上が必要です（現在: $PY_VER）"
  fi
  ok "Python $PY_VER"
else
  fail "Python3 が見つかりません。Python 3.11 以上をインストールしてください。"
fi

# uv
if ! command -v uv &>/dev/null; then
  fail "uv が見つかりません。https://docs.astral.sh/uv/ からインストールしてください。"
fi
ok "uv $(uv --version 2>&1 | awk '{print $2}')"

# Node.js 20+
if command -v node &>/dev/null; then
  NODE_VER=$(node --version | sed 's/v//')
  NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
  if [[ "$NODE_MAJOR" -lt 20 ]]; then
    fail "Node.js 20 以上が必要です（現在: $NODE_VER）"
  fi
  ok "Node.js $NODE_VER"
else
  fail "Node.js が見つかりません。Node.js 20 以上をインストールしてください。"
fi

# npm
if ! command -v npm &>/dev/null; then
  fail "npm が見つかりません。Node.js に含まれているはずです。"
fi
ok "npm $(npm --version)"

echo ""

# ── config.json ───────────────────────────────────────────────────────────────

echo "設定ファイルを準備しています..."

if [[ ! -f config.json ]]; then
  cp config.json.template config.json

  # Discord トークンの取得（引数未指定の場合は対話入力）
  if [[ -z "$DISCORD_TOKEN" ]]; then
    echo ""
    echo -n "Discord Bot トークンを入力してください（スキップは Enter）: "
    read -r DISCORD_TOKEN
  fi

  # その他の必須項目を対話入力
  echo ""
  echo -n "Discord OAuth2 クライアント ID を入力してください（スキップは Enter）: "
  read -r DISCORD_CLIENT_ID

  echo -n "Discord OAuth2 クライアントシークレットを入力してください（スキップは Enter）: "
  read -r DISCORD_CLIENT_SECRET

  echo -n "Bot 管理者の Discord ユーザー ID をカンマ区切りで入力してください（例: 123456789,987654321、スキップは Enter）: "
  read -r BOT_ADMIN_IDS_INPUT

  # Generate random encryption_master_key (32 bytes → base64url, URL-safe)
  if command -v python3 &>/dev/null; then
    ENC_KEY=$(python3 -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())")
    SESSION_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    # Replace placeholder values in config.json
    python3 - <<PYEOF
import json
import pathlib

from src.config import _strip_comments, _strip_trailing_commas

p = pathlib.Path("config.json")
text = p.read_text(encoding="utf-8")
cfg = json.loads(_strip_trailing_commas(_strip_comments(text)))
cfg["encryption_master_key"] = "$ENC_KEY"
cfg["session_secret"] = "$SESSION_SECRET"
if "$DISCORD_TOKEN":
    cfg["discord_token"] = "$DISCORD_TOKEN"
if "$DISCORD_CLIENT_ID":
    cfg["discord_client_id"] = "$DISCORD_CLIENT_ID"
if "$DISCORD_CLIENT_SECRET":
    cfg["discord_client_secret"] = "$DISCORD_CLIENT_SECRET"
if "$BOT_ADMIN_IDS_INPUT":
    cfg["bot_admin_ids"] = [int(x.strip()) for x in "$BOT_ADMIN_IDS_INPUT".split(",") if x.strip().isdigit()]
p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PYEOF
    ok "config.json を作成し、ランダムなキーを生成しました。"
  else
    ok "config.json を作成しました（キーは手動で設定してください）。"
  fi

  echo ""
  MISSING_FIELDS=()
  [[ -z "$DISCORD_TOKEN" ]]         && MISSING_FIELDS+=("  - discord_token        : Discord Bot トークン")
  [[ -z "$DISCORD_CLIENT_ID" ]]     && MISSING_FIELDS+=("  - discord_client_id    : Discord OAuth2 クライアント ID")
  [[ -z "$DISCORD_CLIENT_SECRET" ]] && MISSING_FIELDS+=("  - discord_client_secret: Discord OAuth2 クライアントシークレット")
  [[ -z "$BOT_ADMIN_IDS_INPUT" ]]   && MISSING_FIELDS+=("  - bot_admin_ids        : Bot 管理者の Discord ユーザー ID（数値配列）")

  if [[ ${#MISSING_FIELDS[@]} -gt 0 ]]; then
    warn "config.json を開いて以下の項目を設定してください："
    for field in "${MISSING_FIELDS[@]}"; do
      warn "$field"
    done
  else
    ok "すべての必須項目を config.json に書き込みました。"
  fi
elif [[ -n "$DISCORD_TOKEN" ]]; then
  # config.json はすでに存在するが --token が渡された場合はトークンだけ上書き
  warn "config.json はすでに存在します。discord_token のみ上書きします。"
  python3 - <<PYEOF
import json
import pathlib

from src.config import _strip_comments, _strip_trailing_commas

p = pathlib.Path("config.json")
text = p.read_text(encoding="utf-8")
cfg = json.loads(_strip_trailing_commas(_strip_comments(text)))
cfg["discord_token"] = "$DISCORD_TOKEN"
p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PYEOF
  ok "discord_token を config.json に書き込みました。"
else
  warn "config.json はすでに存在するためスキップします。"
fi

echo ""

# ── Python 依存関係 ────────────────────────────────────────────────────────────

echo "Python 依存関係をインストールしています..."
uv sync --extra web --group dev
ok "Python 依存関係のインストール完了"

echo ""

# ── フロントエンド依存関係 ─────────────────────────────────────────────────────

echo "フロントエンドの依存関係をインストールしています..."
(cd frontend && npm install)
ok "フロントエンド依存関係のインストール完了"

echo ""

# ── 完了メッセージ ─────────────────────────────────────────────────────────────

TOKEN_CONFIGURED=""
if [[ -f config.json ]]; then
  TOKEN_CONFIGURED=$(python3 - <<'PYEOF'
import json
from pathlib import Path

from src.config import _strip_comments, _strip_trailing_commas

text = Path("config.json").read_text(encoding="utf-8")
cfg = json.loads(_strip_trailing_commas(_strip_comments(text)))
print("1" if cfg.get("discord_token") else "")
PYEOF
)
fi

echo "=== セットアップ完了 ==="
echo ""
echo "次のステップ:"
if [[ -n "$TOKEN_CONFIGURED" ]]; then
  echo "  1. config.json の値（web_url / OAuth2設定）を必要に応じて確認する"
else
  echo "  1. config.json を編集して Discord トークン等を設定する"
fi
echo "  2. 起動（Bot + API + フロントエンドビルド）: ./scripts/start-all.sh"
echo ""
echo "開発時（ホットリロードあり）:"
echo "  API/Bot : ./scripts/start-api.sh  /  ./scripts/start-bot.sh"
echo "  Frontend: cd frontend && npm run dev   # ポート 5173"
echo ""
echo "テスト実行:"
echo "  Python : uv run pytest tests/ -v"
echo "  Frontend: cd frontend && npm test"

#!/usr/bin/env bash
# Update script for ideal-bot.
# Pulls the latest code and updates dependencies.
# Docker 環境では --docker オプションを使用してください。
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

DOCKER=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --docker)
      DOCKER=1
      shift
      ;;
    -h|--help)
      echo "使い方: $0 [--docker]"
      echo ""
      echo "  --docker  Docker Compose 環境向けアップデート（イメージ再ビルドまで行う）"
      exit 0
      ;;
    *)
      fail "不明なオプション: $1"
      ;;
  esac
done

echo "=== ideal-bot アップデート ==="
echo ""

# ── git pull ──────────────────────────────────────────────────────────────────

if ! command -v git &>/dev/null; then
  fail "git が見つかりません。"
fi

if [[ ! -d .git ]]; then
  fail "Git リポジトリではありません。ideal-bot のディレクトリで実行してください。"
fi

echo "最新コードを取得しています..."
BEFORE=$(git rev-parse HEAD)
git pull --ff-only || fail "git pull に失敗しました。コンフリクトがある場合は手動で解決してください。"
AFTER=$(git rev-parse HEAD)

if [[ "$BEFORE" == "$AFTER" ]]; then
  ok "すでに最新です（$(git rev-parse --short HEAD)）"
else
  ok "更新しました: $(git rev-parse --short "$BEFORE") → $(git rev-parse --short "$AFTER")"
  echo ""
  git log --oneline "${BEFORE}..${AFTER}"
fi

echo ""

# ── Docker モード ─────────────────────────────────────────────────────────────

if [[ "$DOCKER" -eq 1 ]]; then
  if ! command -v docker &>/dev/null; then
    fail "docker が見つかりません。"
  fi

  echo "Docker イメージを再ビルドして再起動しています..."
  docker compose up --build -d
  ok "Docker コンテナを更新しました。"
  echo ""
  echo "ログを確認するには: docker compose logs -f"
  exit 0
fi

# ── ローカルモード ─────────────────────────────────────────────────────────────

# Python 依存関係の更新
echo "Python 依存関係を更新しています..."
if ! command -v uv &>/dev/null; then
  fail "uv が見つかりません。https://docs.astral.sh/uv/ からインストールしてください。"
fi
uv sync --extra web
ok "Python 依存関係の更新完了"

echo ""

# フロントエンド依存関係の更新とビルド
if command -v npm &>/dev/null && [[ -f frontend/package.json ]]; then
  echo "フロントエンドをビルドしています..."
  (cd frontend && npm install && npm run build)
  ok "フロントエンドのビルド完了"
  echo ""
fi

# ── 完了メッセージ ─────────────────────────────────────────────────────────────

echo "=== アップデート完了 ==="
echo ""
echo "サービスを再起動してください:"
echo "  ./scripts/start-all.sh"
echo ""
echo "データベースのマイグレーションは起動時に自動実行されます。"

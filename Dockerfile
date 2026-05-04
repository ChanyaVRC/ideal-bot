# ── Stage 1: フロントエンドビルド ──────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ── Stage 2: Python 依存関係インストール ────────────────────────────────────────
FROM python:3.12-slim AS python-builder

WORKDIR /app

# uv をインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra web


# ── Stage 3: 実行イメージ ────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# 仮想環境をコピー
COPY --from=python-builder /app/.venv /app/.venv

# アプリケーションコードをコピー
COPY src/ ./src/

# フロントエンドの dist をコピー（FastAPI が /frontend/dist を参照）
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# データディレクトリを作成（DBをマウントする想定）
RUN mkdir -p /data

ENV PATH="/app/.venv/bin:$PATH" \
    DB_PATH=/data/ideal_bot.db \
    LOG_FILE=/data/ideal_bot.log \
    WEB_HOST=0.0.0.0 \
    WEB_PORT=8000 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

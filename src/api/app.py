from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

logger = logging.getLogger(__name__)

from src.config import Config, load_config
from src.db.connection import init_schema, open_db
from src.api.routers.admin_router import router as admin_router
from src.api.routers.auth_router import router as auth_router
from src.api.routers.guilds_router import router as guilds_router


def create_app(cfg: Config | None = None) -> FastAPI:
    if cfg is None:
        cfg = load_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not cfg.session_secret:
            raise ValueError(
                "SESSION_SECRET is not set. "
                "Generate a strong random secret and set it before running in production."
            )
        app.state.cfg = cfg
        app.state.db = await open_db(cfg.db_path)
        await init_schema(app.state.db)
        app.state.http_client = httpx.AsyncClient()
        app.state.guild_cache = {}  # {user_id: {"guilds": list, "fetched_at": datetime}}
        if cfg.log_file:
            from logging.handlers import RotatingFileHandler
            _fh = RotatingFileHandler(
                cfg.log_file,
                maxBytes=cfg.log_max_bytes,
                backupCount=cfg.log_backup_count,
                encoding="utf-8",
            )
            _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
            logging.getLogger().addHandler(_fh)
            logger.info("File logging enabled: %s", cfg.log_file)
        yield
        await app.state.http_client.aclose()
        await app.state.db.close()

    app = FastAPI(title="ideal-bot admin API", lifespan=lifespan)

    app.add_middleware(
        SessionMiddleware,
        # Actual validation of secret_key happens in lifespan; placeholder avoids
        # Starlette rejecting an empty string at middleware registration time.
        secret_key=cfg.session_secret or "placeholder-validated-at-startup",
        session_cookie="ideal_bot_session",
        https_only=cfg.web_url.startswith("https://"),
        same_site="lax",
        max_age=7 * 24 * 3600,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[cfg.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
    app.include_router(guilds_router, prefix="/api/guilds", tags=["guilds"])

    # Serve React build (skipped in dev mode when dist/ doesn't exist)
    dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    if dist.exists():
        index = dist / "index.html"

        # SPA catch-all: serve existing files from dist, otherwise return index.html
        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str):
            candidate = dist / full_path
            if candidate.is_file():
                return FileResponse(str(candidate))
            return FileResponse(str(index))
    else:
        logger.warning(
            "frontend/dist not found — serving API only. "
            "Run `npm run build` in frontend/ or use ./scripts/start-all.sh."
        )

    return app

from __future__ import annotations

# Entrypoint for uvicorn: uvicorn src.api.app:create_app --factory
# Or run directly: uv run python -m src.api.server

if __name__ == "__main__":
    import uvicorn
    from src.config import load_config

    cfg = load_config()
    uvicorn.run(
        "src.api.app:create_app",
        factory=True,
        host=cfg.web_host,
        port=cfg.web_port,
        reload=True,
    )

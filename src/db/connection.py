import logging
import sqlite3
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)


def _is_duplicate_column_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "duplicate column name" in message

# ---------------------------------------------------------------------------
# マイグレーション定義
# src/db/migrations/v{n}.sql を順番に適用します。
# 新しいマイグレーションは v2.sql, v3.sql ... と追加してください。
# ---------------------------------------------------------------------------
_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _load_migrations() -> list[str]:
    """migrations/ ディレクトリから v1.sql, v2.sql ... を順番に読み込む。"""
    sqls: list[str] = []
    version = 1
    while True:
        path = _MIGRATIONS_DIR / f"v{version}.sql"
        if not path.exists():
            break
        sqls.append(path.read_text(encoding="utf-8"))
        version += 1
    return sqls


async def open_db(path: str) -> aiosqlite.Connection:
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_schema(db: aiosqlite.Connection) -> None:
    # foreign_keys を一時的に無効にしてマイグレーション実行（executescript の制約回避）
    await db.execute("PRAGMA foreign_keys=OFF")

    cur = await db.execute("PRAGMA user_version")
    row = await cur.fetchone()
    current_version: int = row[0]

    migrations = _load_migrations()
    target_version = len(migrations)

    if current_version < target_version:
        logger.info(
            "DB マイグレーション実行: v%d → v%d", current_version, target_version
        )
        for i, sql in enumerate(migrations[current_version:], start=current_version + 1):
            logger.info("  マイグレーション v%d を適用中...", i)
            try:
                await db.executescript(sql)
            except sqlite3.OperationalError as exc:
                if _is_duplicate_column_error(exc):
                    logger.warning(
                        "  マイグレーション v%d: duplicate column を検出したためスキップします (%s)",
                        i,
                        exc,
                    )
                else:
                    raise
        # user_version はパラメータバインドできないためフォーマットで設定
        await db.execute(f"PRAGMA user_version = {target_version}")
        await db.commit()
        logger.info("マイグレーション完了 (v%d)", target_version)
    else:
        logger.debug("DB スキーマは最新です (v%d)", current_version)

    await db.execute("PRAGMA foreign_keys=ON")

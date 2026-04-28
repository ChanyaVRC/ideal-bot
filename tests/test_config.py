from __future__ import annotations

from pathlib import Path

from src.config import load_config


def test_load_config_normalizes_bot_admin_ids_to_str(tmp_path: Path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        """
        {
          // required fields
          "discord_token": "token",
          "encryption_master_key": "key",
          "bot_admin_ids": [123456789012345678, "999999999999999999"]
        }
        """,
        encoding="utf-8",
    )

    cfg = load_config(cfg_path)

    assert cfg.bot_admin_ids == ["123456789012345678", "999999999999999999"]

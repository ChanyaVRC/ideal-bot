from __future__ import annotations

import asyncio
import logging
import os

import aiosqlite
import discord
from discord.ext import commands

from src.ai.local import LocalAI
from src.config import Config, load_config
from src.db.connection import init_schema, open_db
from src.db import bot_settings as bot_settings_db
from src.state import BotState

logger = logging.getLogger(__name__)


def _should_sync_commands() -> bool:
    # Default is sync-on-start. Set SYNC_COMMANDS=0 to explicitly skip.
    raw = os.environ.get("SYNC_COMMANDS")
    if raw is None:
        return True
    return raw.strip().lower() not in ("0", "false", "no", "off")

COGS = [
    "src.cogs.teach",
    "src.cogs.wordlist",
    "src.cogs.forget",
    "src.cogs.events",
    "src.cogs.conv",
    "src.cogs.config_cog",
    "src.cogs.speak",
    "src.cogs.reset",
    "src.cogs.dashboard",
]


class IdealBot(commands.Bot):
    db: aiosqlite.Connection
    cfg: Config
    state: BotState
    local_ai: LocalAI

    def __init__(self, cfg: Config) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.cfg = cfg
        self.state = BotState()

    async def setup_hook(self) -> None:
        logger.info("Starting bot initialization...")
        logger.debug("Opening database connection: %s", self.cfg.db_path)
        self.db = await open_db(self.cfg.db_path)
        logger.debug("Database opened. Initializing schema...")
        await init_schema(self.db)
        logger.info("Database is ready.")

        logger.debug(
            "Initializing LocalAI: sentence_model=%s generation_model=%s cpu_only_mode=%s",
            self.cfg.sentence_transformer_model,
            self.cfg.local_generation_model,
            self.cfg.cpu_only_mode,
        )
        self.local_ai = LocalAI(
            self.cfg.sentence_transformer_model,
            generation_model=self.cfg.local_generation_model,
            cpu_only_mode=self.cfg.cpu_only_mode,
        )
        if await self._has_remote_llm():
            self.local_ai.release_generator()
        asyncio.create_task(self.local_ai.preload())
        logger.info("Background AI model loading has started.")

        # Apply any persisted generation config from DB
        dtype = await bot_settings_db.get_value(self.db, "local_torch_dtype")
        quant = await bot_settings_db.get_value(self.db, "local_quantization_mode")
        self.local_ai.update_generation_config(dtype, quant)

        for cog in COGS:
            logger.debug("Loading cog: %s", cog)
            await self.load_extension(cog)
            logger.info("Feature module loaded: %s", cog)

        if _should_sync_commands():
            logger.debug("Syncing command tree...")
            await self.tree.sync()
            logger.info("Slash commands are up to date.")
        else:
            logger.info("Skipped slash command sync due to configuration.")

        asyncio.create_task(self._sync_commands_poller())
        asyncio.create_task(self._reload_generator_poller())
        logger.debug("Sync commands poller task started.")
        logger.info("Bot initialization is complete.")

    async def _sync_commands_poller(self) -> None:
        """Poll bot_settings for a sync request from the admin API."""
        while not self.is_closed():
            await asyncio.sleep(30)
            try:
                flag = await bot_settings_db.get_value(self.db, "sync_commands_requested")
                if flag == "1":
                    await self.tree.sync()
                    await bot_settings_db.set_value(self.db, "sync_commands_requested", "0")
                    logger.info("Command tree re-synced via admin request.")
            except Exception:
                logger.exception("Error in sync commands poller")

    async def _has_remote_llm(self) -> bool:
        return bool(await bot_settings_db.get_value(self.db, "global_llm_api_key")) or \
               bool(await bot_settings_db.get_value(self.db, "vllm_base_url"))

    async def _reload_generator_poller(self) -> None:
        """Poll bot_settings for generator reload requests and remote-LLM state changes."""
        while not self.is_closed():
            await asyncio.sleep(30)
            try:
                has_remote_llm = await self._has_remote_llm()

                flag = await bot_settings_db.get_value(self.db, "reload_generator_requested")
                if flag == "1":
                    await bot_settings_db.set_value(self.db, "reload_generator_requested", "0")
                    if not has_remote_llm:
                        dtype = await bot_settings_db.get_value(self.db, "local_torch_dtype")
                        quant = await bot_settings_db.get_value(self.db, "local_quantization_mode")
                        self.local_ai.update_generation_config(dtype, quant)
                        logger.info("Generator reload requested via admin panel. Reloading...")
                        asyncio.create_task(self.local_ai.reload_generator_async())
                    else:
                        logger.info("Generator reload requested but remote LLM is active; skipping.")

                if has_remote_llm:
                    self.local_ai.release_generator()
                else:
                    self.local_ai.restore_generator()
            except Exception:
                logger.exception("Error in reload generator poller")

    async def on_ready(self) -> None:
        assert self.user is not None
        logger.info("Logged in as %s (ID: %s)", self.user, self.user.id)

    async def close(self) -> None:
        await super().close()
        await self.db.close()
        logger.info("Database connection closed.")


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Starting bot...")
    logger.debug("Loading configuration from config.json")

    config = load_config()
    from src.logging_setup import setup_file_logging
    setup_file_logging(config)
    logger.info("Configuration loaded.")
    logger.info("Log level: %s", config.log_level.upper())
    logger.debug(
        "Startup config: db_path=%s web_url=%s cpu_only_mode=%s sentence_model=%s generation_model=%s",
        config.db_path,
        config.web_url,
        config.cpu_only_mode,
        config.sentence_transformer_model,
        config.local_generation_model,
    )

    bot = IdealBot(cfg=config)
    logger.info("Connecting to Discord...")
    async with bot:
        await bot.start(config.discord_token)


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import asyncio
import logging
import random
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks

from src.ai.generator import generate_response_with_context
from src.db import conversation_log as log_db
from src.db import guild_settings as settings_db

if TYPE_CHECKING:
    from src.main import IdealBot

logger = logging.getLogger(__name__)


class EventsCog(commands.Cog):
    def __init__(self, bot: "IdealBot") -> None:
        self.bot = bot
        self._cleanup_task.start()

    def cog_unload(self) -> None:
        self._cleanup_task.cancel()

    @tasks.loop(minutes=5)
    async def _cleanup_task(self) -> None:
        try:
            retention = self.bot.cfg.conversation_log_retention_days
            await log_db.purge_old_messages(self.bot.db, retention)
            self.bot.state.purge_stale(60)
        except Exception:
            logger.exception("Log cleanup failed")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None or not message.content:
            return

        guild_id = str(message.guild.id)
        channel_id = message.channel.id

        await log_db.add_message(
            self.bot.db,
            guild_id,
            str(channel_id),
            str(message.author.id),
            message.content,
            is_bot=False,
        )
        await log_db.purge_channel(
            self.bot.db, guild_id, str(channel_id)
        )

        settings = await settings_db.ensure_settings(
            self.bot.db, guild_id
        )
        if not settings.bot_enabled:
            return

        state = self.bot.state

        # If already processing this channel, just update conv TTL
        if channel_id in state.processing_channels:
            state.touch(channel_id)
            return

        is_mention = self.bot.user in message.mentions
        is_in_conv = state.is_active(channel_id, settings.conversation_ttl)

        if is_in_conv:
            state.touch(channel_id)
            if state.is_paused(channel_id):
                return
            should_respond = True
        elif is_mention:
            should_respond = True
        else:
            should_respond = random.randint(1, 100) <= settings.reply_rate

        if not should_respond:
            return

        lock = state.get_lock(channel_id)
        if lock.locked():
            state.touch(channel_id)
            return

        async with lock:
            state.processing_channels.add(channel_id)
            state.enter_conversation(channel_id)
            try:
                read_min = settings.delay_read_min or self.bot.cfg.delay_read_min
                read_max = settings.delay_read_max or self.bot.cfg.delay_read_max
                await asyncio.sleep(random.uniform(read_min, read_max))

                async with message.channel.typing():
                    response, reply_context, metadata = await generate_response_with_context(
                        db=self.bot.db,
                        config=self.bot.cfg,
                        local_ai=self.bot.local_ai,
                        guild_id=guild_id,
                        channel_id=str(channel_id),
                        bot_name=self.bot.user.name,
                    )
                    logger.debug("Sending response in guild %s channel %s: %r", guild_id, channel_id, response)
                    type_cps = settings.delay_type_cps or self.bot.cfg.delay_type_cps
                    type_delay = min(8.0, max(1.0, len(response) / type_cps))
                    await asyncio.sleep(type_delay)

                await message.channel.send(response)
                await log_db.add_message(
                    self.bot.db,
                    guild_id,
                    str(channel_id),
                    str(self.bot.user.id),
                    response,
                    is_bot=True,
                    reply_context=reply_context,
                    generation_metadata=metadata,
                )
            except Exception:
                logger.exception("Failed to generate/send response in guild %s", guild_id)
            finally:
                state.processing_channels.discard(channel_id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EventsCog(bot))

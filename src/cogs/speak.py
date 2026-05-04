from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from src.ai.generator import generate_response
from src.db import words as words_db
from src.utils.normalize import get_category_reading

if TYPE_CHECKING:
    from src.main import IdealBot


class SpeakCog(commands.Cog):
    def __init__(self, bot: "IdealBot") -> None:
        self.bot = bot

    @app_commands.command(name="speak", description="Botに発言させます")
    @app_commands.describe(
        category="カテゴリ指定（省略で全カテゴリからランダム）",
        theme="テーマ（LLMモード時はプロンプトに注入、ローカルAI時は類似語彙選択に使用）",
    )
    async def speak(
        self,
        interaction: discord.Interaction,
        category: Optional[str] = None,
        theme: Optional[str] = None,
    ) -> None:
        assert interaction.guild is not None
        await interaction.response.defer()

        guild_id = str(interaction.guild.id)

        if category:
            category_reading = get_category_reading(
                self.bot.cfg.category_normalization,
                category,
            )
            words = await words_db.get_words(
                self.bot.db, guild_id, category_reading
            )
            if not words:
                await interaction.followup.send(
                    f"❌ カテゴリ「{category}」に登録された単語がありません。"
                )
                return

        response = await generate_response(
            db=self.bot.db,
            config=self.bot.cfg,
            local_ai=self.bot.local_ai,
            guild_id=guild_id,
            channel_id=str(interaction.channel_id),
            bot_name=self.bot.user.name,
            theme=theme,
        )
        await interaction.followup.send(response)

    @speak.autocomplete("category")
    async def category_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        if interaction.guild is None:
            return []
        cats = await words_db.get_categories(
            self.bot.db, str(interaction.guild.id)
        )
        return [
            app_commands.Choice(name=c, value=c)
            for c, _ in cats
            if current.lower() in c.lower()
        ][:25]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SpeakCog(bot))

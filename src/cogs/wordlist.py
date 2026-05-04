from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from src.db import words as words_db
from src.utils.normalize import get_category_reading
from src.views.word_list_paginator import WordListPaginator

if TYPE_CHECKING:
    from src.main import IdealBot


class WordListCog(commands.Cog):
    def __init__(self, bot: "IdealBot") -> None:
        self.bot = bot

    @app_commands.command(name="wordlist", description="登録された単語一覧を表示します")
    @app_commands.describe(category="絞り込むカテゴリ（省略で全て）")
    async def wordlist(
        self, interaction: discord.Interaction, category: str | None = None
    ) -> None:
        assert interaction.guild is not None
        guild_id = str(interaction.guild.id)
        category_reading = (
            get_category_reading(self.bot.cfg.category_normalization, category)
            if category
            else None
        )
        word_list = await words_db.get_words(
            self.bot.db, guild_id, category_reading
        )
        paginator = WordListPaginator(word_list)
        await interaction.response.send_message(
            embed=paginator.current_embed(), view=paginator, ephemeral=True
        )

    @wordlist.autocomplete("category")
    async def category_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        if interaction.guild is None:
            return []
        categories = await words_db.get_categories(
            self.bot.db, str(interaction.guild.id)
        )
        current_lower = current.lower()
        return [
            app_commands.Choice(name=cat, value=cat)
            for cat, _ in categories
            if current_lower in cat.lower()
        ][:25]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WordListCog(bot))

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from src.db import words as words_db
from src.utils.normalize import get_word_reading


class ForgetCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="forget", description="単語を削除します")
    @app_commands.describe(word="削除する単語")
    async def forget(
        self, interaction: discord.Interaction, word: str
    ) -> None:
        assert interaction.guild is not None
        guild_id = str(interaction.guild.id)
        reading = get_word_reading(
            self.bot.cfg.category_normalization,  # type: ignore[attr-defined]
            word.strip(),
        )

        existing = await words_db.get_word_by_reading(
            self.bot.db, guild_id, reading  # type: ignore[attr-defined]
        )
        if existing is None:
            await interaction.response.send_message(
                f"❌ 「{word}」は登録されていません。", ephemeral=True
            )
            return

        is_admin = (
            isinstance(interaction.user, discord.Member)
            and interaction.user.guild_permissions.manage_guild
        )
        is_author = existing.added_by == str(interaction.user.id)
        if not is_admin and not is_author:
            await interaction.response.send_message(
                "❌ 削除できるのは登録者本人か、サーバー管理者のみです。", ephemeral=True
            )
            return

        await words_db.delete_word_by_reading(
            self.bot.db, guild_id, reading  # type: ignore[attr-defined]
        )
        await interaction.response.send_message(
            f"🗑️ 「{existing.word}」（{existing.category}）を削除しました。",
            ephemeral=True,
        )

    @forget.autocomplete("word")
    async def word_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        if interaction.guild is None:
            return []
        pairs = await words_db.get_all_words_for_autocomplete(
            self.bot.db, str(interaction.guild.id)  # type: ignore[attr-defined]
        )
        current_lower = current.lower()
        return [
            app_commands.Choice(name=w, value=w)
            for w, _ in pairs
            if current_lower in w.lower()
        ][:25]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ForgetCog(bot))

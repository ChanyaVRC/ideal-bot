from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from src.db import words as words_db

if TYPE_CHECKING:
    from src.main import IdealBot


class ResetConfirmView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=60.0)
        self.confirmed: bool | None = None

    @discord.ui.button(label="✅ はい、全削除する", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.confirmed = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="❌ キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.confirmed = False
        self.stop()
        await interaction.response.defer()


class ResetCog(commands.Cog):
    def __init__(self, bot: "IdealBot") -> None:
        self.bot = bot

    @app_commands.command(name="reset", description="このサーバーの登録単語を全削除します（管理者専用）")
    @app_commands.default_permissions(manage_guild=True)
    async def reset(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        guild_id = str(interaction.guild.id)

        words = await words_db.get_words(self.bot.db, guild_id)
        count = len(words)
        if count == 0:
            await interaction.response.send_message(
                "登録された単語はありません。", ephemeral=True
            )
            return

        view = ResetConfirmView()
        await interaction.response.send_message(
            f"⚠️ **{count}件** の単語を全削除します。本当によいですか？",
            view=view,
            ephemeral=True,
        )
        await view.wait()

        if not view.confirmed:
            await interaction.edit_original_response(
                content="❌ キャンセルしました。", view=discord.ui.View()
            )
            return

        await self.bot.db.execute(
            "DELETE FROM words WHERE guild_id = ?", (guild_id,)
        )
        await self.bot.db.commit()
        await interaction.edit_original_response(
            content=f"🗑️ {count} 件の単語を削除しました。",
            view=discord.ui.View(),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ResetCog(bot))

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from src.main import IdealBot


class DashboardCog(commands.Cog):
    def __init__(self, bot: "IdealBot") -> None:
        self.bot = bot

    @app_commands.command(name="dashboard", description="管理画面のURLを表示します（管理者専用）")
    @app_commands.default_permissions(manage_guild=True)
    async def dashboard(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        web_url = getattr(self.bot.cfg, "web_url", "http://localhost:8000").rstrip("/")
        url = f"{web_url}/guild/{interaction.guild.id}"
        await interaction.response.send_message(
            f"📋 **{interaction.guild.name}** の管理画面:\n{url}"
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DashboardCog(bot))

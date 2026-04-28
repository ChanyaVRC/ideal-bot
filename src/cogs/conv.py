from __future__ import annotations

from datetime import UTC, datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from src.db import guild_settings as settings_db


class ConvCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    conv_group = app_commands.Group(
        name="conv",
        description="会話モードの操作（管理者専用）",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @conv_group.command(name="stop", description="このチャンネルの会話モードを即時終了します")
    async def conv_stop(self, interaction: discord.Interaction) -> None:
        channel_id = interaction.channel_id
        state = self.bot.state  # type: ignore[attr-defined]
        if channel_id not in state.active_channels:
            await interaction.response.send_message(
                "このチャンネルは現在会話モードではありません。", ephemeral=True
            )
            return
        state.stop_conversation(channel_id)
        await interaction.response.send_message(
            "✅ 会話モードを終了しました。", ephemeral=True
        )

    @conv_group.command(name="pause", description="会話モードを N 分間一時停止します")
    @app_commands.describe(minutes="一時停止する分数")
    async def conv_pause(
        self,
        interaction: discord.Interaction,
        minutes: app_commands.Range[int, 1, 1440],
    ) -> None:
        channel_id = interaction.channel_id
        state = self.bot.state  # type: ignore[attr-defined]
        if channel_id not in state.active_channels:
            await interaction.response.send_message(
                "このチャンネルは現在会話モードではありません。", ephemeral=True
            )
            return
        until = datetime.now(UTC) + timedelta(minutes=minutes)
        state.pause_conversation(channel_id, until)
        await interaction.response.send_message(
            f"⏸️ 会話モードを {minutes} 分間一時停止しました。", ephemeral=True
        )

    @conv_group.command(name="status", description="アクティブな会話モードの一覧と残り時間を表示します")
    async def conv_status(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        state = self.bot.state  # type: ignore[attr-defined]
        settings = await settings_db.ensure_settings(
            self.bot.db, str(interaction.guild.id)  # type: ignore[attr-defined]
        )
        ttl = settings.conversation_ttl

        lines: list[str] = []
        for ch_id, ch_state in list(state.active_channels.items()):
            if not state.is_active(ch_id, ttl):
                continue
            channel = interaction.guild.get_channel(ch_id)
            ch_name = channel.mention if channel else f"<#{ch_id}>"
            elapsed = (datetime.now(UTC) - ch_state.last_message_at).total_seconds() / 60
            remaining = ttl - elapsed
            pause_info = ""
            if ch_state.paused_until and datetime.now(UTC) < ch_state.paused_until:
                pause_remaining = (ch_state.paused_until - datetime.now(UTC)).total_seconds() / 60
                pause_info = f"（⏸️ {pause_remaining:.0f}分間停止中）"
            lines.append(f"{ch_name}: 残り {remaining:.0f}分{pause_info}")

        if not lines:
            await interaction.response.send_message(
                "現在アクティブな会話モードはありません。", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="💬 アクティブな会話モード",
            description="\n".join(lines),
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ConvCog(bot))

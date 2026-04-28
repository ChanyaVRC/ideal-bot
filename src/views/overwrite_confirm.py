from __future__ import annotations

import discord


class OverwriteConfirmView(discord.ui.View):
    def __init__(self, *, timeout: float = 60.0) -> None:
        super().__init__(timeout=timeout)
        self.confirmed: bool | None = None

    @discord.ui.button(label="✅ はい", style=discord.ButtonStyle.success)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.confirmed = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="❌ いいえ", style=discord.ButtonStyle.danger)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.confirmed = False
        self.stop()
        await interaction.response.defer()

from __future__ import annotations

import discord
from discord.ext import commands

from src.db.teach_allowlist import AllowlistEntry

PAGE_SIZE = 10


class AllowlistView(discord.ui.View):
    def __init__(self, guild: discord.Guild, entries: list[AllowlistEntry]) -> None:
        super().__init__(timeout=120.0)
        self._guild = guild
        self._roles = [e for e in entries if e.target_type == "role"]
        self._users = [e for e in entries if e.target_type == "user"]
        self._mode: str = "role"
        self._page: int = 0

        self._prev = discord.ui.Button(
            label="◀ 前へ", style=discord.ButtonStyle.secondary, disabled=True
        )
        self._next = discord.ui.Button(
            label="▶ 次へ", style=discord.ButtonStyle.secondary
        )
        self._toggle = discord.ui.Button(
            label="👤 ユーザー一覧へ", style=discord.ButtonStyle.primary
        )
        self._prev.callback = self._on_prev
        self._next.callback = self._on_next
        self._toggle.callback = self._on_toggle
        self.add_item(self._prev)
        self.add_item(self._next)
        self.add_item(self._toggle)
        self._update_buttons()

    def _current_list(self) -> list[AllowlistEntry]:
        return self._roles if self._mode == "role" else self._users

    def _total_pages(self) -> int:
        return max(1, (len(self._current_list()) + PAGE_SIZE - 1) // PAGE_SIZE)

    def _update_buttons(self) -> None:
        self._prev.disabled = self._page == 0
        self._next.disabled = self._page >= self._total_pages() - 1
        if self._mode == "role":
            self._toggle.label = "👤 ユーザー一覧へ"
        else:
            self._toggle.label = "📋 ロール一覧へ"

    def current_embed(self) -> discord.Embed:
        entries = self._current_list()
        total = self._total_pages()
        page_entries = entries[self._page * PAGE_SIZE : (self._page + 1) * PAGE_SIZE]

        if self._mode == "role":
            title = f"📋 ロール ({self._page + 1}/{total})"
        else:
            title = f"👤 ユーザー ({self._page + 1}/{total})"

        embed = discord.Embed(title="許可リスト — " + title, color=discord.Color.blurple())
        lines: list[str] = []
        for entry in page_entries:
            if entry.target_type == "role":
                role = self._guild.get_role(int(entry.target_id))
                lines.append(role.mention if role else f"<@&{entry.target_id}>（削除済み）")
            else:
                lines.append(f"<@{entry.target_id}>")

        embed.description = "\n".join(lines) if lines else "（なし）"
        return embed

    async def _on_prev(self, interaction: discord.Interaction) -> None:
        self._page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.current_embed(), view=self)

    async def _on_next(self, interaction: discord.Interaction) -> None:
        self._page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.current_embed(), view=self)

    async def _on_toggle(self, interaction: discord.Interaction) -> None:
        self._mode = "user" if self._mode == "role" else "role"
        self._page = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self.current_embed(), view=self)

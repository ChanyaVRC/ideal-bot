from __future__ import annotations

import discord

from src.db.words import Word

PAGE_SIZE = 10


class WordListPaginator(discord.ui.View):
    def __init__(self, words: list[Word], *, timeout: float = 120.0) -> None:
        super().__init__(timeout=timeout)
        self.words = words
        self.page = 0
        self.total_pages = max(1, (len(words) + PAGE_SIZE - 1) // PAGE_SIZE)

        self._prev = discord.ui.Button(
            label="◀ 前へ",
            style=discord.ButtonStyle.secondary,
            disabled=True,
        )
        self._next = discord.ui.Button(
            label="▶ 次へ",
            style=discord.ButtonStyle.secondary,
            disabled=self.total_pages <= 1,
        )
        self._prev.callback = self._on_prev
        self._next.callback = self._on_next
        self.add_item(self._prev)
        self.add_item(self._next)

    def current_embed(self) -> discord.Embed:
        start = self.page * PAGE_SIZE
        page_words = self.words[start : start + PAGE_SIZE]
        embed = discord.Embed(title="📚 登録単語一覧", color=discord.Color.blurple())
        if not page_words:
            embed.description = "単語が登録されていません。"
        else:
            embed.description = "\n".join(
                f"**{w.word}**　{w.category}" for w in page_words
            )
        embed.set_footer(
            text=f"ページ {self.page + 1}/{self.total_pages}　全 {len(self.words)} 件"
        )
        return embed

    async def _on_prev(self, interaction: discord.Interaction) -> None:
        self.page -= 1
        self._prev.disabled = self.page == 0
        self._next.disabled = False
        await interaction.response.edit_message(embed=self.current_embed(), view=self)

    async def _on_next(self, interaction: discord.Interaction) -> None:
        self.page += 1
        self._next.disabled = self.page >= self.total_pages - 1
        self._prev.disabled = False
        await interaction.response.edit_message(embed=self.current_embed(), view=self)

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from src.db import teach_allowlist as allowlist_db
from src.db import words as words_db
from src.utils.normalize import get_word_reading, resolve_category
from src.views.overwrite_confirm import OverwriteConfirmView

if TYPE_CHECKING:
    from src.main import IdealBot


async def _compute_embedding(bot: commands.Bot, text: str) -> bytes | None:
    local_ai = getattr(bot, "local_ai", None)
    if local_ai is None:
        return None
    try:
        import numpy as np
        emb = await local_ai.encode_async(text)
        return emb.astype(np.float32).tobytes()
    except Exception:
        return None


class TeachCog(commands.Cog):
    def __init__(self, bot: "IdealBot") -> None:
        self.bot = bot

    @app_commands.command(name="teach", description="単語を登録します")
    @app_commands.describe(
        word="登録する単語（例: ふわふわ、どきどき、猫）",
        category="カテゴリ（例: 形容詞、感情、挨拶）",
    )
    async def teach(
        self, interaction: discord.Interaction, word: str, category: str
    ) -> None:
        assert interaction.guild is not None

        role_ids = (
            [r.id for r in interaction.user.roles]
            if isinstance(interaction.user, discord.Member)
            else []
        )
        allowed = await allowlist_db.can_teach(
            self.bot.db,
            str(interaction.guild.id),
            interaction.user.id,
            role_ids,
        )
        if not allowed:
            await interaction.response.send_message(
                "❌ 単語を登録する権限がありません。", ephemeral=True
            )
            return

        word = word.strip()
        category = category.strip()
        if not word or not category:
            await interaction.response.send_message(
                "❌ 単語とカテゴリを入力してください。", ephemeral=True
            )
            return

        reading = get_word_reading(
            self.bot.cfg.category_normalization,
            word,
        )
        guild_id = str(interaction.guild.id)
        category, category_reading = await resolve_category(
            self.bot.cfg.category_normalization,
            self.bot.local_ai,
            self.bot.db,
            guild_id,
            category,
        )

        existing = await words_db.get_word_by_reading(
            self.bot.db, guild_id, reading
        )

        if existing is not None:
            view = OverwriteConfirmView()
            await interaction.response.send_message(
                f"⚠️ 「{existing.word}」はすでに「{existing.category}」として登録されています。上書きしますか？",
                view=view,
                ephemeral=True,
            )
            await view.wait()
            if not view.confirmed:
                await interaction.edit_original_response(
                    content="❌ キャンセルしました。", view=discord.ui.View()
                )
                return
            await words_db.upsert_word(
                self.bot.db,
                guild_id=guild_id,
                word=word,
                reading=reading,
                category=category,
                category_reading=category_reading,
                added_by=str(interaction.user.id),
                embedding=await _compute_embedding(self.bot, word),
            )
            await interaction.edit_original_response(
                content=f"✅ 「{word}」を「{category}」として上書き登録しました！",
                view=discord.ui.View(),
            )
        else:
            await words_db.insert_word(
                self.bot.db,
                guild_id=guild_id,
                word=word,
                reading=reading,
                category=category,
                category_reading=category_reading,
                added_by=str(interaction.user.id),
                embedding=await _compute_embedding(self.bot, word),
            )
            await interaction.response.send_message(
                f"✅ 「{word}」を「{category}」として登録しました！", ephemeral=True
            )

    @teach.autocomplete("category")
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
    await bot.add_cog(TeachCog(bot))

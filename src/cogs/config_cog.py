from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from src.db import guild_settings as settings_db
from src.db import teach_allowlist as allowlist_db
from src.utils.encryption import encrypt

if TYPE_CHECKING:
    from src.main import IdealBot

PROVIDERS = ["openai", "gemini"]
MODELS = [
    "gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini",
    "gemini-2.0-flash", "gemini-2.5-pro", "gemini-1.5-flash",
]


def _admin_check(interaction: discord.Interaction) -> bool:
    if not isinstance(interaction.user, discord.Member):
        return False
    return interaction.user.guild_permissions.manage_guild


class ConfigCog(commands.Cog):
    def __init__(self, bot: "IdealBot") -> None:
        self.bot = bot

    config_group = app_commands.Group(
        name="config",
        description="サーバー設定（管理者専用）",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    # ── reply_rate ──────────────────────────────────────────────────
    @config_group.command(name="reply_rate", description="Botの反応確率を設定します（0-100%）")
    @app_commands.describe(rate="反応確率（0で反応なし、100で毎回反応）")
    async def reply_rate(
        self,
        interaction: discord.Interaction,
        rate: app_commands.Range[int, 0, 100],
    ) -> None:
        assert interaction.guild is not None
        await settings_db.update_setting(
            self.bot.db, str(interaction.guild.id), reply_rate=rate
        )
        await interaction.response.send_message(
            f"✅ 反応確率を **{rate}%** に設定しました。", ephemeral=True
        )

    # ── bot on/off ───────────────────────────────────────────────────
    @config_group.command(name="bot", description="このサーバーでのBotの反応を有効/無効にします")
    @app_commands.describe(enabled="on = 有効, off = 無効")
    @app_commands.choices(enabled=[
        app_commands.Choice(name="on", value=1),
        app_commands.Choice(name="off", value=0),
    ])
    async def bot_toggle(
        self, interaction: discord.Interaction, enabled: int
    ) -> None:
        assert interaction.guild is not None
        await settings_db.update_setting(
            self.bot.db, str(interaction.guild.id), bot_enabled=bool(enabled)
        )
        label = "有効" if enabled else "無効"
        await interaction.response.send_message(
            f"✅ Botの反応を **{label}** にしました。", ephemeral=True
        )

    # ── delay ────────────────────────────────────────────────────────
    @config_group.command(name="delay", description="応答遅延パラメータを設定します")
    @app_commands.describe(
        read_min="読み取り遅延の最小秒数",
        read_max="読み取り遅延の最大秒数",
        type_cps="タイピング速度（文字/秒）",
    )
    async def delay(
        self,
        interaction: discord.Interaction,
        read_min: Optional[app_commands.Range[float, 0.0, 30.0]] = None,
        read_max: Optional[app_commands.Range[float, 0.0, 30.0]] = None,
        type_cps: Optional[app_commands.Range[float, 1.0, 100.0]] = None,
    ) -> None:
        assert interaction.guild is not None
        kwargs: dict[str, float] = {}
        if read_min is not None:
            kwargs["delay_read_min"] = read_min
        if read_max is not None:
            kwargs["delay_read_max"] = read_max
        if type_cps is not None:
            kwargs["delay_type_cps"] = type_cps
        if not kwargs:
            await interaction.response.send_message(
                "変更する項目を1つ以上指定してください。", ephemeral=True
            )
            return
        await settings_db.update_setting(
            self.bot.db, str(interaction.guild.id), **kwargs
        )
        parts = [f"{k}={v}" for k, v in kwargs.items()]
        await interaction.response.send_message(
            f"✅ 遅延パラメータを更新しました: {', '.join(parts)}", ephemeral=True
        )

    # ── teach_allow ──────────────────────────────────────────────────
    @config_group.command(name="teach_allow", description="単語登録の許可リストにロール/ユーザーを追加、またはeveryoneに戻します")
    @app_commands.describe(
        role="許可するロール",
        user="許可するユーザー",
    )
    async def teach_allow(
        self,
        interaction: discord.Interaction,
        role: Optional[discord.Role] = None,
        user: Optional[discord.Member] = None,
    ) -> None:
        assert interaction.guild is not None
        guild_id = str(interaction.guild.id)
        if role is None and user is None:
            await allowlist_db.clear_allowlist(self.bot.db, guild_id)
            await interaction.response.send_message(
                "✅ 許可リストをリセットしました。全員が登録可能です。", ephemeral=True
            )
        elif role is not None:
            await allowlist_db.add_to_allowlist(
                self.bot.db, guild_id, str(role.id), "role"
            )
            await interaction.response.send_message(
                f"✅ {role.mention} を許可リストに追加しました。", ephemeral=True
            )
        else:
            await allowlist_db.add_to_allowlist(
                self.bot.db, guild_id, str(user.id), "user"
            )
            await interaction.response.send_message(
                f"✅ {user.mention} を許可リストに追加しました。", ephemeral=True
            )

    # ── teach_deny ───────────────────────────────────────────────────
    @config_group.command(name="teach_deny", description="許可リストからロール/ユーザーを除外します")
    @app_commands.describe(
        role="除外するロール",
        user="除外するユーザー",
    )
    async def teach_deny(
        self,
        interaction: discord.Interaction,
        role: Optional[discord.Role] = None,
        user: Optional[discord.Member] = None,
    ) -> None:
        assert interaction.guild is not None
        guild_id = str(interaction.guild.id)
        if role is None and user is None:
            await interaction.response.send_message(
                "除外するロールまたはユーザーを指定してください。", ephemeral=True
            )
            return
        target = role or user
        target_id = str(target.id)
        removed = await allowlist_db.remove_from_allowlist(
            self.bot.db, guild_id, target_id
        )
        if removed:
            await interaction.response.send_message(
                f"✅ {target.mention} を許可リストから除外しました。", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ {target.mention} は許可リストに存在しませんでした。", ephemeral=True
            )

    # ── teach_list ───────────────────────────────────────────────────
    @config_group.command(name="teach_list", description="登録許可リストを表示します")
    async def teach_list(self, interaction: discord.Interaction) -> None:
        assert interaction.guild is not None
        guild_id = str(interaction.guild.id)
        entries = await allowlist_db.get_allowlist(
            self.bot.db, guild_id
        )
        if not entries:
            await interaction.response.send_message(
                "📋 許可リストは空です（全員が登録可能）。", ephemeral=True
            )
            return

        from src.views.allowlist_view import AllowlistView
        view = AllowlistView(interaction.guild, entries)
        await interaction.response.send_message(
            embed=view.current_embed(), view=view, ephemeral=True
        )

    # ── apikey ───────────────────────────────────────────────────────
    @config_group.command(name="apikey", description="LLM APIキーを登録します")
    @app_commands.describe(
        provider="プロバイダー（openai / gemini）",
        key="APIキー",
    )
    @app_commands.choices(provider=[
        app_commands.Choice(name=p, value=p) for p in PROVIDERS
    ])
    async def apikey(
        self,
        interaction: discord.Interaction,
        provider: str,
        key: str,
    ) -> None:
        assert interaction.guild is not None
        encrypted = encrypt(self.bot.cfg.encryption_master_key, key)
        await settings_db.update_setting(
            self.bot.db,
            str(interaction.guild.id),
            llm_api_key=encrypted,
            llm_provider=provider,
        )
        await interaction.response.send_message(
            f"✅ {provider} の API キーを登録しました。", ephemeral=True
        )

    # ── model ────────────────────────────────────────────────────────
    @config_group.command(name="model", description="使用するLLMモデルを設定します")
    @app_commands.describe(model_name="モデル名（一覧から選択、または直接入力）")
    async def model(
        self, interaction: discord.Interaction, model_name: str
    ) -> None:
        assert interaction.guild is not None
        await settings_db.update_setting(
            self.bot.db, str(interaction.guild.id), llm_model=model_name
        )
        await interaction.response.send_message(
            f"✅ LLM モデルを **{model_name}** に設定しました。", ephemeral=True
        )

    @model.autocomplete("model_name")
    async def model_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=m, value=m)
            for m in MODELS
            if current.lower() in m.lower()
        ][:25]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ConfigCog(bot))

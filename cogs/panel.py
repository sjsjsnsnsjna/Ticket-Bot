import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

from cogs.tickets import CategoryView

LOG_CHANNEL_ID = 1518636444141355190
SUPPORT_ROLE_ID = 1520083680666714143
OWNER_ROLE_ID = 1518636371072389264


class PanelEditModal(discord.ui.Modal, title="Panel Düzenle"):
    panel_title = discord.ui.TextInput(
        label="Başlık",
        placeholder="🎫 Destek Merkezi",
        required=False,
        max_length=100,
    )
    description = discord.ui.TextInput(
        label="Açıklama",
        placeholder="Destek almak için kategori seçin.",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500,
    )
    color = discord.ui.TextInput(
        label="Renk (Hex)",
        placeholder="5865F2",
        required=False,
        max_length=10,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.stop()


class PanelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _is_admin(self, member: discord.Member) -> bool:
        return member.guild_permissions.administrator

    @app_commands.command(name="panel-kur", description="Destek panelini kurar (Admin)")
    async def panel_kur(self, interaction: discord.Interaction):
        if not self._is_admin(interaction.user):
            await interaction.response.send_message("Bu komutu kullanma yetkiniz yok.", ephemeral=True)
            return

        settings = await self.bot.db.get_guild_settings(interaction.guild_id)

        title = "🎫 Destek Merkezi"
        description = (
            "Merhaba! Destek ekibimize ulaşmak için aşağıdan uygun kategoriyi seçin.\n\n"
            "🛠️ **Teknik Destek** — Teknik sorunlar\n"
            "💰 **Satın Alma** — Satın alma işlemleri\n"
            "📢 **Şikayet** — Şikayetler\n"
            "💡 **Diğer** — Diğer konular"
        )
        color = 0x5865F2

        if settings:
            if settings["panel_title"]:
                title = settings["panel_title"]
            if settings["panel_description"]:
                description = settings["panel_description"]
            if settings["panel_color"]:
                color = settings["panel_color"]

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(
            text=interaction.guild.name,
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
        )

        view = CategoryView()
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Panel başarıyla kuruldu!", ephemeral=True)

    @app_commands.command(name="panel-düzenle", description="Destek panelini düzenler (Admin)")
    async def panel_duzenle(self, interaction: discord.Interaction):
        if not self._is_admin(interaction.user):
            await interaction.response.send_message("Bu komutu kullanma yetkiniz yok.", ephemeral=True)
            return

        modal = PanelEditModal()
        await interaction.response.send_modal(modal)
        await modal.wait()

        kwargs = {}
        if modal.panel_title.value:
            kwargs["panel_title"] = modal.panel_title.value
        if modal.description.value:
            kwargs["panel_description"] = modal.description.value
        if modal.color.value:
            try:
                color_val = int(modal.color.value.strip("#"), 16)
                kwargs["panel_color"] = color_val
            except ValueError:
                pass

        if kwargs:
            await self.bot.db.save_guild_settings(interaction.guild_id, **kwargs)

        await interaction.followup.send(
            "✅ Panel ayarları güncellendi. Yeni panel kurmak için `/panel-kur` kullanın.",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(PanelCog(bot))

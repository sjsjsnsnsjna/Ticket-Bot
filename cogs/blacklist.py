import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

from utils import embeds as emb

LOG_CHANNEL_ID = 1518636444141355190


class BlacklistCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _is_admin(self, member: discord.Member) -> bool:
        return member.guild_permissions.administrator

    @app_commands.command(name="kara-liste-ekle", description="Kullanıcıyı kara listeye ekler (Admin)")
    @app_commands.describe(kullanici="Kara listeye eklenecek kullanıcı", sebep="Kara listeye ekleme sebebi")
    async def blacklist_add(self, interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Belirtilmedi"):
        if not self._is_admin(interaction.user):
            await interaction.response.send_message("Bu komutu kullanma yetkiniz yok.", ephemeral=True)
            return

        await self.bot.db.add_blacklist(kullanici.id, interaction.guild_id, interaction.user.id, sebep)

        embed = discord.Embed(
            title="🚫 Kara Listeye Eklendi",
            description=f"{kullanici.mention} kara listeye eklendi.",
            color=0xED4245,
        )
        embed.add_field(name="📝 Sebep", value=sebep)
        await interaction.response.send_message(embed=embed)

        log_ch = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            await log_ch.send(embed=emb.blacklist_added_embed(kullanici, sebep, interaction.user, interaction.guild))

    @app_commands.command(name="kara-liste-çıkar", description="Kullanıcıyı kara listeden çıkarır (Admin)")
    @app_commands.describe(kullanici="Kara listeden çıkarılacak kullanıcı")
    async def blacklist_remove(self, interaction: discord.Interaction, kullanici: discord.Member):
        if not self._is_admin(interaction.user):
            await interaction.response.send_message("Bu komutu kullanma yetkiniz yok.", ephemeral=True)
            return

        await self.bot.db.remove_blacklist(kullanici.id, interaction.guild_id)

        embed = discord.Embed(
            title="✅ Kara Listeden Çıkarıldı",
            description=f"{kullanici.mention} kara listeden çıkarıldı.",
            color=0x57F287,
        )
        await interaction.response.send_message(embed=embed)

        log_ch = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            await log_ch.send(embed=emb.blacklist_removed_embed(kullanici, interaction.user, interaction.guild))

    @app_commands.command(name="kara-liste-görüntüle", description="Kara listedeki kullanıcıları gösterir")
    async def blacklist_view(self, interaction: discord.Interaction):
        blacklist = await self.bot.db.get_blacklist(interaction.guild_id)

        if not blacklist:
            embed = discord.Embed(
                title="🚫 Kara Liste",
                description="Kara listede kimse yok.",
                color=0x5865F2,
            )
            await interaction.response.send_message(embed=embed)
            return

        embed = discord.Embed(
            title=f"🚫 Kara Liste — {len(blacklist)} Kullanıcı",
            color=0xED4245,
            timestamp=datetime.now(timezone.utc),
        )

        for entry in blacklist[:25]:
            added_by = interaction.guild.get_member(entry["added_by"])
            added_by_str = str(added_by) if added_by else f"ID:{entry['added_by']}"
            try:
                added_at = datetime.fromisoformat(entry["added_at"]).strftime("%d.%m.%Y")
            except Exception:
                added_at = entry["added_at"]
            embed.add_field(
                name=f"<@{entry['user_id']}>",
                value=f"**Sebep:** {entry['reason']}\n**Ekleyen:** {added_by_str}\n**Tarih:** {added_at}",
                inline=True,
            )

        embed.set_footer(text=interaction.guild.name)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(BlacklistCog(bot))

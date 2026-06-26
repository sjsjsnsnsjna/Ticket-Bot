import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone


class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="istatistik", description="Ticket istatistiklerini gösterir")
    async def stats(self, interaction: discord.Interaction):
        await interaction.response.defer()
        data = await self.bot.db.get_stats(interaction.guild_id)

        avg_close = data["avg_close"]
        if avg_close:
            hours = int(avg_close // 3600)
            minutes = int((avg_close % 3600) // 60)
            avg_str = f"{hours}s {minutes}d"
        else:
            avg_str = "Veri yok"

        top_staff = None
        if data["top_staff"]:
            member = interaction.guild.get_member(data["top_staff"])
            top_staff = member.mention if member else f"<@{data['top_staff']}>"

        category_names = {
            "technical": "🛠️ Teknik Destek",
            "purchase": "💰 Satın Alma",
            "complaint": "📢 Şikayet",
            "other": "💡 Diğer",
        }
        top_cat = category_names.get(data["top_category"], data["top_category"]) if data["top_category"] else "Veri yok"

        embed = discord.Embed(
            title="📊 Ticket İstatistikleri",
            color=0x5865F2,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="🎫 Toplam Ticket", value=str(data["total"]), inline=True)
        embed.add_field(name="🟢 Açık Ticket", value=str(data["open"]), inline=True)
        embed.add_field(name="📅 Bugün Açılan", value=str(data["today"]), inline=True)
        embed.add_field(name="⏱️ Ort. Kapanma Süresi", value=avg_str, inline=True)
        embed.add_field(name="👷 En Aktif Yetkili", value=top_staff or "Veri yok", inline=True)
        embed.add_field(name="📂 En Çok Kullanılan Kategori", value=top_cat, inline=True)
        embed.set_footer(
            text=interaction.guild.name,
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="değerlendirme-rapor", description="Yetkili değerlendirme raporunu gösterir")
    async def rating_report(self, interaction: discord.Interaction):
        await interaction.response.defer()
        rows = await self.bot.db.get_rating_report(interaction.guild_id)

        embed = discord.Embed(
            title="⭐ Değerlendirme Raporu",
            color=0xFEE75C,
            timestamp=datetime.now(timezone.utc),
        )

        if not rows:
            embed.description = "Henüz değerlendirme bulunmuyor."
            await interaction.followup.send(embed=embed)
            return

        highest_avg = float(rows[0]["avg_rating"]) if rows else 0
        best_staff = None

        for i, row in enumerate(rows[:10]):
            member = interaction.guild.get_member(row["staff_id"])
            name = member.display_name if member else f"ID:{row['staff_id']}"
            avg = float(row["avg_rating"])
            total = row["total"]
            stars = "⭐" * round(avg)
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"`#{i+1}`"
            embed.add_field(
                name=f"{medal} {name}",
                value=f"{stars}\n**Ort:** {avg:.1f} / 5\n**Toplam:** {total} değerlendirme",
                inline=True,
            )
            if i == 0:
                best_staff = name

        if best_staff:
            embed.description = f"🏆 En yüksek puan: **{best_staff}** ({highest_avg:.1f} ⭐)"

        embed.set_footer(
            text=interaction.guild.name,
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
        )
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(StatsCog(bot))

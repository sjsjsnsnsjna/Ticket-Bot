import discord
from discord.ext import commands, tasks
import asyncio
import io
from datetime import datetime, timezone, timedelta

from utils import embeds as emb
from utils.transcript import generate_transcript

LOG_CHANNEL_ID = 1518636444141355190
SUPPORT_ROLE_ID = 1520083680666714143

WARNING_HOURS = 24
CLOSE_HOURS = 48


class AutoCloseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warned_channels: set = set()
        self.auto_close_task.start()

    def cog_unload(self):
        self.auto_close_task.cancel()

    @tasks.loop(minutes=30)
    async def auto_close_task(self):
        tickets = await self.bot.db.get_all_open_tickets()
        now = datetime.now(timezone.utc)

        for ticket in tickets:
            channel_id = ticket["channel_id"]
            guild = self.bot.get_guild(ticket["guild_id"])
            if not guild:
                continue
            channel = guild.get_channel(channel_id)
            if not channel:
                continue

            last_message_time = None
            try:
                async for msg in channel.history(limit=10):
                    if not msg.author.bot:
                        last_message_time = msg.created_at
                        break
            except (discord.Forbidden, discord.NotFound):
                continue

            if not last_message_time:
                try:
                    created_at = datetime.fromisoformat(ticket["created_at"]).replace(tzinfo=timezone.utc)
                    last_message_time = created_at
                except Exception:
                    continue

            idle_seconds = (now - last_message_time).total_seconds()
            idle_hours = idle_seconds / 3600

            if idle_hours >= CLOSE_HOURS:
                await self._auto_close(channel, ticket, guild, idle_hours)
            elif idle_hours >= WARNING_HOURS and channel_id not in self.warned_channels:
                await self._send_warning(channel, ticket, guild)
                self.warned_channels.add(channel_id)

    async def _send_warning(self, channel: discord.TextChannel, ticket, guild: discord.Guild):
        user = guild.get_member(ticket["user_id"])
        warn_embed = discord.Embed(
            title="⏰ Hareketsizlik Uyarısı",
            description=(
                f"Bu ticket **{WARNING_HOURS} saattir** hareketsiz.\n"
                f"Eğer **{CLOSE_HOURS} saat** içinde mesaj gönderilmezse ticket otomatik olarak kapatılacaktır."
            ),
            color=0xFF8C00,
            timestamp=datetime.now(timezone.utc),
        )
        try:
            await channel.send(
                content=user.mention if user else None,
                embed=warn_embed,
            )
        except (discord.Forbidden, discord.NotFound):
            pass

        if user:
            try:
                dm_embed = discord.Embed(
                    title="⏰ Ticket Uyarısı",
                    description=(
                        f"**#{ticket['id']}** numaralı ticketınız **{WARNING_HOURS} saattir** hareketsiz.\n"
                        "Eğer yanıt vermezseniz ticket otomatik kapatılacaktır."
                    ),
                    color=0xFF8C00,
                )
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass

    async def _auto_close(self, channel: discord.TextChannel, ticket, guild: discord.Guild, idle_hours: float):
        reason = f"{CLOSE_HOURS} saatlik hareketsizlik"
        await self.bot.db.close_ticket(channel.id, reason)
        ticket = await self.bot.db.get_ticket_by_channel(channel.id)
        if not ticket:
            return

        notes = await self.bot.db.get_notes(ticket["id"])
        try:
            html_bytes = await generate_transcript(channel, ticket, guild, notes, SUPPORT_ROLE_ID)
        except Exception:
            html_bytes = "<html><body>Transkript olusturulamadi.</body></html>".encode("utf-8")

        log_ch = guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            file = discord.File(io.BytesIO(html_bytes), filename=f"ticket-{ticket['id']}.html")
            await log_ch.send(
                embed=emb.auto_closed_embed(ticket["id"], reason, int(idle_hours), guild),
                file=file,
            )

        self.warned_channels.discard(channel.id)

        close_embed = discord.Embed(
            title="⏰ Ticket Otomatik Kapatıldı",
            description=f"Bu ticket **{CLOSE_HOURS} saatlik** hareketsizlik nedeniyle kapatıldı.",
            color=0xFF8C00,
        )
        try:
            await channel.send(embed=close_embed)
            await asyncio.sleep(5)
            await channel.delete(reason="Otomatik kapatıldı")
        except (discord.Forbidden, discord.NotFound):
            pass

    @auto_close_task.before_loop
    async def before_auto_close(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(AutoCloseCog(bot))

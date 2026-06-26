import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import io
from datetime import datetime, timezone

from utils import embeds as emb
from utils.transcript import generate_transcript

LOG_CHANNEL_ID = 1518636444141355190
SUPPORT_ROLE_ID = 1520083680666714143
OWNER_ROLE_ID = 1518636371072389264

CATEGORY_LABELS = {
    "technical": "🛠️ Teknik Destek",
    "purchase": "💰 Satın Alma",
    "complaint": "📢 Şikayet",
    "other": "💡 Diğer",
}

PRIORITY_EMOJIS = {"low": "🟢", "medium": "🟡", "high": "🔴", "urgent": "🚨"}
PRIORITY_LABELS = {"low": "Düşük", "medium": "Orta", "high": "Yüksek", "urgent": "Acil"}
LABEL_LABELS = {"resolved": "✅ Çözüldü", "waiting": "⏳ Beklemede", "investigating": "🔍 İnceleniyor", "rejected": "❌ Reddedildi"}


class CloseReasonModal(discord.ui.Modal, title="Ticket Kapatma"):
    reason = discord.ui.TextInput(
        label="Kapatma Sebebi",
        placeholder="Ticketı kapatma sebebinizi girin...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.stop()


class NoteModal(discord.ui.Modal, title="Not Ekle"):
    note = discord.ui.TextInput(
        label="Not",
        placeholder="Not içeriğini girin...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.stop()


class AddUserModal(discord.ui.Modal, title="Kullanıcı Ekle"):
    user_id = discord.ui.TextInput(
        label="Kullanıcı ID",
        placeholder="Eklenecek kullanıcının ID'sini girin",
        required=True,
        max_length=25,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.stop()


class RatingView(discord.ui.View):
    def __init__(self, ticket_id: int, user_id: int, staff_id: int, bot):
        super().__init__(timeout=86400)
        self.ticket_id = ticket_id
        self.user_id = user_id
        self.staff_id = staff_id
        self.bot = bot

        for i in range(1, 6):
            btn = discord.ui.Button(
                label=f"{'⭐' * i}",
                custom_id=f"rate_{ticket_id}_{i}",
                style=discord.ButtonStyle.secondary,
            )
            btn.callback = self._make_callback(i)
            self.add_item(btn)

    def _make_callback(self, rating: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("Bu değerlendirme size ait değil.", ephemeral=True)
                return
            await self.bot.db.save_rating(self.ticket_id, self.user_id, self.staff_id, rating)
            await interaction.response.edit_message(
                embed=emb.rating_thanks_embed(rating), view=None
            )
        return callback


class TicketButtonView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def _get_ticket(self, channel_id):
        return await self.bot.db.get_ticket_by_channel(channel_id)

    async def _send_log(self, guild, embed, file=None):
        log_ch = guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            if file:
                await log_ch.send(embed=embed, file=file)
            else:
                await log_ch.send(embed=embed)

    def _has_support(self, member, guild):
        role = guild.get_role(SUPPORT_ROLE_ID)
        return role in member.roles if role else False

    @discord.ui.button(label="🔒 Kapat", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = await self._get_ticket(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message("Bu kanal bir ticket değil.", ephemeral=True)
            return

        modal = CloseReasonModal()
        await interaction.response.send_modal(modal)
        await modal.wait()

        reason = modal.reason.value
        await self.bot.db.close_ticket(interaction.channel_id, reason, interaction.user.id)
        ticket = await self._get_ticket(interaction.channel_id)

        notes = await self.bot.db.get_notes(ticket["id"])
        html_bytes = await generate_transcript(interaction.channel, ticket, interaction.guild, notes, SUPPORT_ROLE_ID)

        staff = interaction.guild.get_member(ticket["owner_id"]) if ticket["owner_id"] else None
        user = interaction.guild.get_member(ticket["user_id"])

        log_embed = emb.ticket_closed_embed(ticket, user, staff, interaction.guild)
        file = discord.File(io.BytesIO(html_bytes), filename=f"ticket-{ticket['id']}.html")
        await self._send_log(interaction.guild, log_embed, file)

        if user:
            try:
                dm_embed = discord.Embed(
                    title="🔒 Ticketınız Kapatıldı",
                    description=f"**Sebep:** {reason}",
                    color=0xED4245,
                )
                created_at = datetime.fromisoformat(ticket["created_at"]).replace(tzinfo=timezone.utc)
                duration = datetime.now(timezone.utc) - created_at
                hours, rem = divmod(int(duration.total_seconds()), 3600)
                minutes, _ = divmod(rem, 60)
                dm_embed.add_field(name="⏱️ Süre", value=f"{hours}s {minutes}d")
                dm_file = discord.File(io.BytesIO(html_bytes), filename=f"ticket-{ticket['id']}.html")
                await user.send(embed=dm_embed, file=dm_file)

                rating_view = RatingView(ticket["id"], user.id, ticket["owner_id"] or interaction.user.id, self.bot)
                await user.send(embed=emb.rating_request_embed(ticket["id"]), view=rating_view)
            except discord.Forbidden:
                pass

        close_embed = discord.Embed(
            title="🔒 Ticket Kapatılıyor",
            description=f"**Sebep:** {reason}\nBu kanal 5 saniye içinde silinecek.",
            color=0xED4245,
        )
        try:
            await interaction.followup.send(embed=close_embed)
        except Exception:
            pass
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason="Ticket kapatıldı")
        except discord.NotFound:
            pass

    @discord.ui.button(label="👤 Sahiplen", style=discord.ButtonStyle.primary, custom_id="ticket_claim")
    async def claim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._has_support(interaction.user, interaction.guild):
            await interaction.response.send_message("Bu butonu kullanma yetkiniz yok.", ephemeral=True)
            return
        ticket = await self._get_ticket(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message("Ticket bulunamadı.", ephemeral=True)
            return
        await self.bot.db.set_ticket_owner(interaction.channel_id, interaction.user.id)
        await interaction.channel.edit(topic=f"Yetkili: {interaction.user}")
        claim_embed = discord.Embed(
            title="👤 Ticket Sahiplenildi",
            description=f"{interaction.user.mention} bu ticketi üstlendi.",
            color=0xFEE75C,
        )
        await interaction.response.send_message(embed=claim_embed)
        await self._send_log(interaction.guild, emb.claimed_embed(ticket["id"], interaction.user, interaction.guild))

    @discord.ui.button(label="⚡ Öncelik", style=discord.ButtonStyle.secondary, custom_id="ticket_priority")
    async def priority_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._has_support(interaction.user, interaction.guild):
            await interaction.response.send_message("Bu butonu kullanma yetkiniz yok.", ephemeral=True)
            return
        ticket = await self._get_ticket(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message("Ticket bulunamadı.", ephemeral=True)
            return

        options = [
            discord.SelectOption(label="Düşük", value="low", emoji="🟢"),
            discord.SelectOption(label="Orta", value="medium", emoji="🟡"),
            discord.SelectOption(label="Yüksek", value="high", emoji="🔴"),
            discord.SelectOption(label="Acil", value="urgent", emoji="🚨"),
        ]

        class PrioritySelect(discord.ui.View):
            def __init__(self, bot_ref, ticket_ref, old_priority):
                super().__init__(timeout=60)
                self.bot_ref = bot_ref
                self.ticket_ref = ticket_ref
                self.old_priority = old_priority

            @discord.ui.select(placeholder="Öncelik seçin...", options=options, custom_id="priority_select_inline")
            async def select_callback(self, inner_inter: discord.Interaction, select: discord.ui.Select):
                new_priority = select.values[0]
                await self.bot_ref.db.set_ticket_priority(inner_inter.channel_id, new_priority)
                emoji = PRIORITY_EMOJIS.get(new_priority, "")
                try:
                    base = inner_inter.channel.name.split("-", 1)
                    base_name = base[-1].replace("🟢-", "").replace("🟡-", "").replace("🔴-", "").replace("🚨-", "")
                    await inner_inter.channel.edit(name=f"{emoji}-{base_name}")
                except Exception:
                    pass
                p_embed = discord.Embed(
                    title="⚡ Öncelik Güncellendi",
                    description=f"Öncelik **{PRIORITY_LABELS.get(new_priority, new_priority)}** olarak ayarlandı.",
                    color=0xEB459E,
                )
                await inner_inter.response.edit_message(embed=p_embed, view=None)
                log_ch = inner_inter.guild.get_channel(LOG_CHANNEL_ID)
                if log_ch:
                    await log_ch.send(embed=emb.priority_changed_embed(
                        self.ticket_ref["id"], self.old_priority, new_priority, inner_inter.user, inner_inter.guild
                    ))

        view = PrioritySelect(self.bot, ticket, ticket["priority"])
        await interaction.response.send_message("Yeni önceliği seçin:", view=view, ephemeral=True)

    @discord.ui.button(label="🏷️ Etiket", style=discord.ButtonStyle.secondary, custom_id="ticket_label")
    async def label_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._has_support(interaction.user, interaction.guild):
            await interaction.response.send_message("Bu butonu kullanma yetkiniz yok.", ephemeral=True)
            return
        ticket = await self._get_ticket(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message("Ticket bulunamadı.", ephemeral=True)
            return

        options = [
            discord.SelectOption(label="Çözüldü", value="resolved", emoji="✅"),
            discord.SelectOption(label="Beklemede", value="waiting", emoji="⏳"),
            discord.SelectOption(label="İnceleniyor", value="investigating", emoji="🔍"),
            discord.SelectOption(label="Reddedildi", value="rejected", emoji="❌"),
        ]

        class LabelSelect(discord.ui.View):
            def __init__(self, bot_ref, ticket_ref):
                super().__init__(timeout=60)
                self.bot_ref = bot_ref
                self.ticket_ref = ticket_ref

            @discord.ui.select(placeholder="Etiket seçin...", options=options, custom_id="label_select_inline")
            async def select_callback(self, inner_inter: discord.Interaction, select: discord.ui.Select):
                new_label = select.values[0]
                await self.bot_ref.db.set_ticket_label(inner_inter.channel_id, new_label)
                l_embed = discord.Embed(
                    title="🏷️ Etiket Güncellendi",
                    description=f"Etiket **{LABEL_LABELS.get(new_label, new_label)}** olarak ayarlandı.",
                    color=0x5865F2,
                )
                await inner_inter.response.edit_message(embed=l_embed, view=None)
                log_ch = inner_inter.guild.get_channel(LOG_CHANNEL_ID)
                if log_ch:
                    await log_ch.send(embed=emb.label_changed_embed(
                        self.ticket_ref["id"], new_label, inner_inter.user, inner_inter.guild
                    ))

        view = LabelSelect(self.bot, ticket)
        await interaction.response.send_message("Etiket seçin:", view=view, ephemeral=True)

    @discord.ui.button(label="📌 Not Ekle", style=discord.ButtonStyle.secondary, custom_id="ticket_note")
    async def note_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._has_support(interaction.user, interaction.guild):
            await interaction.response.send_message("Bu butonu kullanma yetkiniz yok.", ephemeral=True)
            return
        ticket = await self._get_ticket(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message("Ticket bulunamadı.", ephemeral=True)
            return
        modal = NoteModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        note_text = modal.note.value
        await self.bot.db.add_note(ticket["id"], interaction.user.id, note_text)
        note_embed = discord.Embed(
            title="📌 Yetkili Notu",
            description=note_text,
            color=0xFEE75C,
        )
        note_embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        await interaction.channel.send(embed=note_embed)
        log_ch = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            await log_ch.send(embed=emb.note_added_embed(ticket["id"], interaction.user, note_text, interaction.guild))

    @discord.ui.button(label="➕ Kullanıcı Ekle", style=discord.ButtonStyle.secondary, custom_id="ticket_adduser")
    async def adduser_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._has_support(interaction.user, interaction.guild):
            await interaction.response.send_message("Bu butonu kullanma yetkiniz yok.", ephemeral=True)
            return
        ticket = await self._get_ticket(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message("Ticket bulunamadı.", ephemeral=True)
            return
        modal = AddUserModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        try:
            uid = int(modal.user_id.value.strip())
            member = interaction.guild.get_member(uid) or await interaction.guild.fetch_member(uid)
            await interaction.channel.set_permissions(member, read_messages=True, send_messages=True)
            added_embed = discord.Embed(
                description=f"✅ {member.mention} kanala eklendi.",
                color=0x57F287,
            )
            await interaction.followup.send(embed=added_embed, ephemeral=True)
            log_ch = interaction.guild.get_channel(LOG_CHANNEL_ID)
            if log_ch:
                await log_ch.send(embed=emb.user_added_embed(ticket["id"], member, interaction.user, interaction.guild))
        except (ValueError, discord.NotFound):
            await interaction.followup.send("Geçersiz kullanıcı ID'si.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Hata oluştu: {e}", ephemeral=True)


class CategoryDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Teknik Destek", value="technical", emoji="🛠️", description="Teknik sorunlar için"),
            discord.SelectOption(label="Satın Alma", value="purchase", emoji="💰", description="Satın alma işlemleri için"),
            discord.SelectOption(label="Şikayet", value="complaint", emoji="📢", description="Şikayetleriniz için"),
            discord.SelectOption(label="Diğer", value="other", emoji="💡", description="Diğer konular için"),
        ]
        super().__init__(
            placeholder="Destek kategorisi seçin...",
            options=options,
            custom_id="ticket_category_select",
        )

    async def callback(self, interaction: discord.Interaction):
        bot = interaction.client
        guild = interaction.guild
        user = interaction.user
        category = self.values[0]

        if await bot.db.is_blacklisted(user.id, guild.id):
            try:
                bl_embed = discord.Embed(
                    title="🚫 Kara Listede",
                    description="Ticket açma yetkiniz kaldırılmıştır. Yetkililere başvurun.",
                    color=0xED4245,
                )
                await user.send(embed=bl_embed)
            except discord.Forbidden:
                pass
            await interaction.response.send_message("Ticket açma yetkiniz yok.", ephemeral=True)
            return

        existing = await bot.db.get_open_ticket_by_user(user.id, guild.id)
        if existing:
            ch = guild.get_channel(existing["channel_id"])
            try:
                ex_embed = discord.Embed(
                    title="❗ Zaten Açık Ticketınız Var",
                    description=f"Mevcut ticketınız: {ch.mention if ch else 'Kanal bulunamadı'}",
                    color=0xFEE75C,
                )
                await user.send(embed=ex_embed)
            except discord.Forbidden:
                pass
            await interaction.response.send_message("Zaten açık bir ticketınız var.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        settings = await bot.db.get_guild_settings(guild.id)
        category_obj = None
        if settings and settings["ticket_category_id"]:
            category_obj = guild.get_channel(settings["ticket_category_id"])

        support_role = guild.get_role(SUPPORT_ROLE_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        safe_name = "".join(c for c in user.display_name if c.isalnum() or c in "-_").lower() or "kullanici"
        channel = await guild.create_text_channel(
            name=f"ticket-{safe_name}",
            overwrites=overwrites,
            category=category_obj,
            reason=f"Ticket açıldı: {user}",
        )

        ticket_id = await bot.db.create_ticket(channel.id, user.id, guild.id, category)

        cat_label = CATEGORY_LABELS.get(category, category)
        welcome_embed = discord.Embed(
            title=f"🎫 Ticket #{ticket_id} — {cat_label}",
            description=(
                f"Merhaba {user.mention}! Destek ekibimiz en kısa sürede yardımcı olacak.\n\n"
                f"**Kategori:** {cat_label}\n"
                f"Lütfen sorununuzu detaylı bir şekilde açıklayın."
            ),
            color=0x5865F2,
            timestamp=datetime.now(timezone.utc),
        )
        welcome_embed.set_footer(text=guild.name, icon_url=guild.icon.url if guild.icon else None)

        view = TicketButtonView(bot)
        await channel.send(content=user.mention, embed=welcome_embed, view=view)

        log_ch = guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            await log_ch.send(embed=emb.ticket_opened_embed(ticket_id, user, category, channel, guild))

        await interaction.followup.send(f"Ticketınız oluşturuldu: {channel.mention}", ephemeral=True)


class CategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CategoryDropdown())


class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(TicketButtonView(self.bot))
        self.bot.add_view(CategoryView())

    @app_commands.command(name="zorla-kapat", description="Bir ticketi zorla kapatır (Sadece Sahibi)")
    @app_commands.describe(kanal="Kapatılacak ticket kanalı")
    async def force_close(self, interaction: discord.Interaction, kanal: discord.TextChannel):
        owner_role = interaction.guild.get_role(OWNER_ROLE_ID)
        if owner_role not in interaction.user.roles:
            await interaction.response.send_message("Bu komutu kullanma yetkiniz yok.", ephemeral=True)
            return

        ticket = await self.bot.db.get_ticket_by_channel(kanal.id)
        if not ticket:
            await interaction.response.send_message("Bu kanal bir ticket değil.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        warning_embed = discord.Embed(
            title="⚠️ Ticket Zorla Kapatılıyor!",
            description=f"Bu ticket **5** saniye içinde zorla kapatılıyor!\n**Yetkili:** {interaction.user.mention}",
            color=0xFF0000,
        )
        try:
            msg = await kanal.send(embed=warning_embed)
            for i in range(4, 0, -1):
                await asyncio.sleep(1)
                warning_embed.description = (
                    f"Bu ticket **{i}** saniye içinde zorla kapatılıyor!\n**Yetkili:** {interaction.user.mention}"
                )
                await msg.edit(embed=warning_embed)
            await asyncio.sleep(1)
        except discord.NotFound:
            pass

        await self.bot.db.close_ticket(kanal.id, "Zorla kapatıldı", interaction.user.id)
        ticket = await self.bot.db.get_ticket_by_channel(kanal.id)
        notes = await self.bot.db.get_notes(ticket["id"])
        html_bytes = await generate_transcript(kanal, ticket, interaction.guild, notes, SUPPORT_ROLE_ID)

        log_ch = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_ch:
            file = discord.File(io.BytesIO(html_bytes), filename=f"ticket-{ticket['id']}.html")
            await log_ch.send(
                embed=emb.force_closed_embed(ticket["id"], kanal.name, interaction.user, interaction.guild),
                file=file,
            )

        try:
            await kanal.delete(reason="Zorla kapatıldı")
        except discord.NotFound:
            pass

        await interaction.followup.send("Ticket zorla kapatıldı.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        ticket = await self.bot.db.get_ticket_by_channel(message.channel.id)
        if ticket and ticket["status"] == "open":
            await self.bot.db.increment_message_count(message.channel.id)


async def setup(bot):
    await bot.add_cog(TicketCog(bot))

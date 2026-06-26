import discord
from datetime import datetime, timezone

LOG_CHANNEL_ID = 1518636444141355190

PRIORITY_EMOJIS = {
    "low": "🟢",
    "medium": "🟡",
    "high": "🔴",
    "urgent": "🚨",
}

PRIORITY_LABELS = {
    "low": "Düşük",
    "medium": "Orta",
    "high": "Yüksek",
    "urgent": "Acil",
}

LABEL_EMOJIS = {
    "resolved": "✅",
    "waiting": "⏳",
    "investigating": "🔍",
    "rejected": "❌",
}

LABEL_LABELS = {
    "resolved": "Çözüldü",
    "waiting": "Beklemede",
    "investigating": "İnceleniyor",
    "rejected": "Reddedildi",
}

CATEGORY_LABELS = {
    "technical": "🛠️ Teknik Destek",
    "purchase": "💰 Satın Alma",
    "complaint": "📢 Şikayet",
    "other": "💡 Diğer",
}


def now_str():
    return discord.utils.format_dt(datetime.now(timezone.utc), style="F")


def _footer(guild):
    return {"text": guild.name if guild else "Ticket Sistemi", "icon_url": guild.icon.url if guild and guild.icon else None}


def ticket_opened_embed(ticket_id, user, category, channel, guild):
    e = discord.Embed(
        title="🎫 Yeni Ticket Açıldı",
        color=0x57F287,
        timestamp=datetime.now(timezone.utc),
    )
    e.add_field(name="🆔 Ticket ID", value=f"`#{ticket_id}`", inline=True)
    e.add_field(name="👤 Kullanıcı", value=user.mention, inline=True)
    e.add_field(name="📂 Kategori", value=CATEGORY_LABELS.get(category, category), inline=True)
    e.add_field(name="📌 Kanal", value=channel.mention, inline=True)
    e.add_field(name="🕒 Zaman", value=now_str(), inline=True)
    e.set_author(name=str(user), icon_url=user.display_avatar.url)
    e.set_footer(**_footer(guild))
    return e


def ticket_closed_embed(ticket, user, staff, guild):
    created_at = datetime.fromisoformat(ticket["created_at"]).replace(tzinfo=timezone.utc)
    closed_at = datetime.now(timezone.utc)
    duration = closed_at - created_at
    hours, rem = divmod(int(duration.total_seconds()), 3600)
    minutes, seconds = divmod(rem, 60)
    duration_str = f"{hours}s {minutes}d {seconds}sn"

    e = discord.Embed(
        title="🔒 Ticket Kapatıldı",
        color=0xED4245,
        timestamp=closed_at,
    )
    e.add_field(name="🆔 Ticket ID", value=f"`#{ticket['id']}`", inline=True)
    e.add_field(name="👤 Kullanıcı", value=user.mention if user else f"<@{ticket['user_id']}>", inline=True)
    e.add_field(name="👷 Yetkili", value=staff.mention if staff else "Atanmamış", inline=True)
    e.add_field(name="📝 Kapatma Sebebi", value=ticket["close_reason"] or "Belirtilmedi", inline=False)
    e.add_field(name="⏱️ Süre", value=duration_str, inline=True)
    e.add_field(name="💬 Mesaj Sayısı", value=str(ticket["message_count"]), inline=True)
    e.set_footer(**_footer(guild))
    return e


def claimed_embed(ticket_id, staff, guild):
    e = discord.Embed(
        title="👤 Ticket Sahiplenildi",
        color=0xFEE75C,
        timestamp=datetime.now(timezone.utc),
    )
    e.add_field(name="🆔 Ticket ID", value=f"`#{ticket_id}`", inline=True)
    e.add_field(name="👷 Yetkili", value=staff.mention, inline=True)
    e.add_field(name="🕒 Zaman", value=now_str(), inline=True)
    e.set_author(name=str(staff), icon_url=staff.display_avatar.url)
    e.set_footer(**_footer(guild))
    return e


def priority_changed_embed(ticket_id, old_priority, new_priority, by_user, guild):
    old_label = f"{PRIORITY_EMOJIS.get(old_priority, '')} {PRIORITY_LABELS.get(old_priority, old_priority)}"
    new_label = f"{PRIORITY_EMOJIS.get(new_priority, '')} {PRIORITY_LABELS.get(new_priority, new_priority)}"
    e = discord.Embed(
        title="⚡ Öncelik Değiştirildi",
        color=0xEB459E,
        timestamp=datetime.now(timezone.utc),
    )
    e.add_field(name="🆔 Ticket ID", value=f"`#{ticket_id}`", inline=True)
    e.add_field(name="📊 Eski → Yeni", value=f"{old_label} → {new_label}", inline=True)
    e.add_field(name="👤 Değiştiren", value=by_user.mention, inline=True)
    e.set_footer(**_footer(guild))
    return e


def label_changed_embed(ticket_id, label, by_user, guild):
    label_str = f"{LABEL_EMOJIS.get(label, '')} {LABEL_LABELS.get(label, label)}"
    e = discord.Embed(
        title="🏷️ Etiket Değiştirildi",
        color=0x5865F2,
        timestamp=datetime.now(timezone.utc),
    )
    e.add_field(name="🆔 Ticket ID", value=f"`#{ticket_id}`", inline=True)
    e.add_field(name="🏷️ Etiket", value=label_str, inline=True)
    e.add_field(name="👤 Değiştiren", value=by_user.mention, inline=True)
    e.set_footer(**_footer(guild))
    return e


def note_added_embed(ticket_id, staff, note, guild):
    e = discord.Embed(
        title="📌 Not Eklendi",
        color=0xFEE75C,
        timestamp=datetime.now(timezone.utc),
    )
    e.add_field(name="🆔 Ticket ID", value=f"`#{ticket_id}`", inline=True)
    e.add_field(name="👷 Yetkili", value=staff.mention, inline=True)
    e.add_field(name="📝 Not Önizleme", value=note[:200] + ("..." if len(note) > 200 else ""), inline=False)
    e.set_footer(**_footer(guild))
    return e


def user_added_embed(ticket_id, target_user, by_user, guild):
    e = discord.Embed(
        title="➕ Kullanıcı Eklendi",
        color=0x57F287,
        timestamp=datetime.now(timezone.utc),
    )
    e.add_field(name="🆔 Ticket ID", value=f"`#{ticket_id}`", inline=True)
    e.add_field(name="👤 Kullanıcı", value=target_user.mention, inline=True)
    e.add_field(name="👤 Ekleyen", value=by_user.mention, inline=True)
    e.set_footer(**_footer(guild))
    return e


def blacklist_added_embed(user, reason, by_user, guild):
    e = discord.Embed(
        title="🚫 Kara Listeye Eklendi",
        color=0xED4245,
        timestamp=datetime.now(timezone.utc),
    )
    e.add_field(name="👤 Kullanıcı", value=user.mention, inline=True)
    e.add_field(name="👤 Ekleyen", value=by_user.mention, inline=True)
    e.add_field(name="📝 Sebep", value=reason or "Belirtilmedi", inline=False)
    e.set_footer(**_footer(guild))
    return e


def blacklist_removed_embed(user, by_user, guild):
    e = discord.Embed(
        title="✅ Kara Listeden Çıkarıldı",
        color=0x57F287,
        timestamp=datetime.now(timezone.utc),
    )
    e.add_field(name="👤 Kullanıcı", value=user.mention, inline=True)
    e.add_field(name="👤 Çıkaran", value=by_user.mention, inline=True)
    e.set_footer(**_footer(guild))
    return e


def force_closed_embed(ticket_id, channel_name, by_user, guild):
    e = discord.Embed(
        title="⚠️ Ticket Zorla Kapatıldı",
        color=0xFF0000,
        timestamp=datetime.now(timezone.utc),
    )
    e.add_field(name="🆔 Ticket ID", value=f"`#{ticket_id}`", inline=True)
    e.add_field(name="📌 Kanal", value=f"`#{channel_name}`", inline=True)
    e.add_field(name="👤 Kapatan", value=by_user.mention, inline=True)
    e.add_field(name="🕒 Zaman", value=now_str(), inline=True)
    e.set_footer(**_footer(guild))
    return e


def auto_closed_embed(ticket_id, reason, duration_hours, guild):
    e = discord.Embed(
        title="⏰ Ticket Otomatik Kapatıldı",
        color=0xFF8C00,
        timestamp=datetime.now(timezone.utc),
    )
    e.add_field(name="🆔 Ticket ID", value=f"`#{ticket_id}`", inline=True)
    e.add_field(name="📝 Sebep", value=reason, inline=True)
    e.add_field(name="⏱️ Süre", value=f"{duration_hours} saat hareketsizlik", inline=True)
    e.set_footer(**_footer(guild))
    return e


def rating_request_embed(ticket_id):
    e = discord.Embed(
        title="⭐ Destek Değerlendirmesi",
        description=(
            f"**#{ticket_id}** numaralı ticketınız kapatıldı.\n"
            "Aldığınız desteği değerlendirmenizi rica ederiz!"
        ),
        color=0xFEE75C,
        timestamp=datetime.now(timezone.utc),
    )
    return e


def rating_thanks_embed(rating):
    stars = "⭐" * rating
    e = discord.Embed(
        title="🙏 Değerlendirmeniz Alındı",
        description=f"**{stars}** puan verdiniz. Geri bildiriminiz için teşekkürler!",
        color=0x57F287,
    )
    return e

import discord
from jinja2 import Environment, BaseLoader
from datetime import datetime, timezone

TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ticket #{{ ticket_id }} - Transkript</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #36393f; color: #dcddde; font-family: 'Whitney', 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 16px; }
  .header { background: #2f3136; padding: 20px 30px; border-bottom: 1px solid #202225; display: flex; align-items: center; gap: 16px; }
  .header img { width: 48px; height: 48px; border-radius: 50%; }
  .header-text h1 { color: #fff; font-size: 20px; font-weight: 700; }
  .header-text p { color: #b9bbbe; font-size: 14px; }
  .info-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; padding: 20px 30px; background: #2f3136; border-bottom: 1px solid #202225; }
  .info-card { background: #202225; border-radius: 6px; padding: 12px 16px; }
  .info-card .label { color: #b9bbbe; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 4px; }
  .info-card .value { color: #fff; font-size: 14px; }
  .messages { padding: 20px 30px; max-width: 100%; }
  .message { display: flex; gap: 16px; margin-bottom: 16px; padding: 4px 0; }
  .avatar { width: 40px; height: 40px; border-radius: 50%; background: #5865f2; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 16px; color: #fff; flex-shrink: 0; text-transform: uppercase; }
  .message-body { flex: 1; }
  .message-header { display: flex; align-items: baseline; gap: 8px; margin-bottom: 4px; }
  .username { font-weight: 600; font-size: 14px; }
  .username.staff { color: #5865f2; }
  .username.user { color: #57f287; }
  .timestamp { color: #72767d; font-size: 11px; }
  .content { color: #dcddde; font-size: 14px; line-height: 1.4; white-space: pre-wrap; word-break: break-word; }
  .attachment { margin-top: 6px; }
  .attachment a { color: #00aff4; font-size: 13px; }
  .notes-section { background: #2f3136; border-left: 4px solid #fee75c; margin: 0 30px 20px; border-radius: 0 6px 6px 0; padding: 16px; }
  .notes-section h3 { color: #fee75c; font-size: 14px; font-weight: 700; margin-bottom: 12px; text-transform: uppercase; letter-spacing: .5px; }
  .note { background: #202225; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; }
  .note .note-author { color: #b9bbbe; font-size: 12px; margin-bottom: 4px; }
  .note .note-text { color: #dcddde; font-size: 13px; }
  .footer { text-align: center; padding: 16px; color: #72767d; font-size: 12px; border-top: 1px solid #202225; }
</style>
</head>
<body>
<div class="header">
  <div class="header-text">
    <h1>{{ guild_name }} — Ticket #{{ ticket_id }}</h1>
    <p>Transkript raporu</p>
  </div>
</div>
<div class="info-grid">
  <div class="info-card"><div class="label">Ticket ID</div><div class="value">#{{ ticket_id }}</div></div>
  <div class="info-card"><div class="label">Kategori</div><div class="value">{{ category }}</div></div>
  <div class="info-card"><div class="label">Durum</div><div class="value">{{ status }}</div></div>
  <div class="info-card"><div class="label">Kullanıcı</div><div class="value">{{ user }}</div></div>
  <div class="info-card"><div class="label">Yetkili</div><div class="value">{{ staff }}</div></div>
  <div class="info-card"><div class="label">Öncelik</div><div class="value">{{ priority }}</div></div>
  <div class="info-card"><div class="label">Açılış Tarihi</div><div class="value">{{ opened_at }}</div></div>
  <div class="info-card"><div class="label">Kapanış Tarihi</div><div class="value">{{ closed_at }}</div></div>
  <div class="info-card"><div class="label">Süre</div><div class="value">{{ duration }}</div></div>
  <div class="info-card"><div class="label">Mesaj Sayısı</div><div class="value">{{ message_count }}</div></div>
  <div class="info-card"><div class="label">Kapatma Sebebi</div><div class="value">{{ close_reason }}</div></div>
  <div class="info-card"><div class="label">Etiket</div><div class="value">{{ label }}</div></div>
</div>
{% if notes %}
<div class="notes-section">
  <h3>📌 Yetkili Notları</h3>
  {% for note in notes %}
  <div class="note">
    <div class="note-author">{{ note.author }} — {{ note.created_at }}</div>
    <div class="note-text">{{ note.text }}</div>
  </div>
  {% endfor %}
</div>
{% endif %}
<div class="messages">
{% for msg in messages %}
  <div class="message">
    <div class="avatar">{{ msg.avatar_letter }}</div>
    <div class="message-body">
      <div class="message-header">
        <span class="username {{ 'staff' if msg.is_staff else 'user' }}">{{ msg.username }}</span>
        <span class="timestamp">{{ msg.timestamp }}</span>
      </div>
      {% if msg.content %}<div class="content">{{ msg.content }}</div>{% endif %}
      {% for att in msg.attachments %}
      <div class="attachment"><a href="{{ att.url }}" target="_blank">📎 {{ att.filename }}</a></div>
      {% endfor %}
    </div>
  </div>
{% endfor %}
</div>
<div class="footer">
  Bu transkript otomatik olarak oluşturulmuştur · {{ guild_name }} Ticket Sistemi
</div>
</body>
</html>"""

CATEGORY_LABELS = {
    "technical": "🛠️ Teknik Destek",
    "purchase": "💰 Satın Alma",
    "complaint": "📢 Şikayet",
    "other": "💡 Diğer",
}

PRIORITY_LABELS = {
    "low": "🟢 Düşük",
    "medium": "🟡 Orta",
    "high": "🔴 Yüksek",
    "urgent": "🚨 Acil",
    "normal": "⚪ Normal",
}

LABEL_LABELS = {
    "resolved": "✅ Çözüldü",
    "waiting": "⏳ Beklemede",
    "investigating": "🔍 İnceleniyor",
    "rejected": "❌ Reddedildi",
}


async def generate_transcript(channel: discord.TextChannel, ticket: dict, guild: discord.Guild, notes: list, support_role_id: int) -> bytes:
    messages = []
    async for msg in channel.history(limit=None, oldest_first=True):
        if msg.author.bot:
            continue
        member = guild.get_member(msg.author.id)
        is_staff = False
        if member:
            support_role = guild.get_role(support_role_id)
            if support_role and support_role in member.roles:
                is_staff = True
        messages.append({
            "avatar_letter": msg.author.display_name[0].upper() if msg.author.display_name else "?",
            "username": str(msg.author),
            "is_staff": is_staff,
            "timestamp": msg.created_at.strftime("%d.%m.%Y %H:%M"),
            "content": msg.content,
            "attachments": [{"url": a.url, "filename": a.filename} for a in msg.attachments],
        })

    created_at = datetime.fromisoformat(ticket["created_at"]).replace(tzinfo=timezone.utc)
    closed_at_raw = ticket["closed_at"]
    if closed_at_raw:
        closed_at = datetime.fromisoformat(closed_at_raw).replace(tzinfo=timezone.utc)
    else:
        closed_at = datetime.now(timezone.utc)
    duration = closed_at - created_at
    hours, rem = divmod(int(duration.total_seconds()), 3600)
    minutes, seconds = divmod(rem, 60)
    duration_str = f"{hours}s {minutes}d {seconds}sn"

    staff_member = guild.get_member(ticket["owner_id"]) if ticket["owner_id"] else None

    note_data = []
    for n in notes:
        author_member = guild.get_member(n["author_id"])
        note_data.append({
            "author": str(author_member) if author_member else f"<@{n['author_id']}>",
            "created_at": datetime.fromisoformat(n["created_at"]).strftime("%d.%m.%Y %H:%M"),
            "text": n["note"],
        })

    user_member = guild.get_member(ticket["user_id"])
    env = Environment(loader=BaseLoader())
    template = env.from_string(TEMPLATE)
    html = template.render(
        guild_name=guild.name,
        ticket_id=ticket["id"],
        category=CATEGORY_LABELS.get(ticket["category"], ticket["category"]),
        status="Açık" if ticket["status"] == "open" else "Kapalı",
        user=str(user_member) if user_member else f"ID:{ticket['user_id']}",
        staff=str(staff_member) if staff_member else "Atanmamış",
        priority=PRIORITY_LABELS.get(ticket["priority"], ticket["priority"] or "Normal"),
        opened_at=created_at.strftime("%d.%m.%Y %H:%M"),
        closed_at=closed_at.strftime("%d.%m.%Y %H:%M"),
        duration=duration_str,
        message_count=ticket["message_count"],
        close_reason=ticket["close_reason"] or "Belirtilmedi",
        label=LABEL_LABELS.get(ticket["label"], ticket["label"] or "-"),
        messages=messages,
        notes=note_data,
    )
    return html.encode("utf-8")

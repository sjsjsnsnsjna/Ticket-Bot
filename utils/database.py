import aiosqlite
import asyncio
from datetime import datetime

DB_PATH = "tickets.db"


class Database:
    def __init__(self):
        self._lock = asyncio.Lock()

    async def initialize(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER UNIQUE,
                    user_id INTEGER,
                    guild_id INTEGER,
                    category TEXT,
                    status TEXT DEFAULT 'open',
                    priority TEXT DEFAULT 'normal',
                    owner_id INTEGER,
                    created_at TEXT,
                    closed_at TEXT,
                    close_reason TEXT,
                    message_count INTEGER DEFAULT 0,
                    label TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS blacklist (
                    user_id INTEGER,
                    guild_id INTEGER,
                    added_by INTEGER,
                    added_at TEXT,
                    reason TEXT,
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ratings (
                    ticket_id INTEGER,
                    user_id INTEGER,
                    staff_id INTEGER,
                    rating INTEGER,
                    created_at TEXT,
                    PRIMARY KEY (ticket_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ticket_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER,
                    author_id INTEGER,
                    note TEXT,
                    created_at TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    support_role_id INTEGER,
                    owner_role_id INTEGER,
                    log_channel_id INTEGER,
                    ticket_category_id INTEGER,
                    panel_color INTEGER DEFAULT 5793266,
                    panel_title TEXT DEFAULT '🎫 Destek Merkezi',
                    panel_description TEXT DEFAULT 'Destek almak için aşağıdan kategori seçin.'
                )
            """)
            await db.commit()

    async def create_ticket(self, channel_id, user_id, guild_id, category):
        async with aiosqlite.connect(DB_PATH) as db:
            now = datetime.utcnow().isoformat()
            await db.execute("""
                INSERT INTO tickets (channel_id, user_id, guild_id, category, status, created_at)
                VALUES (?, ?, ?, ?, 'open', ?)
            """, (channel_id, user_id, guild_id, category, now))
            await db.commit()
            cursor = await db.execute("SELECT last_insert_rowid()")
            row = await cursor.fetchone()
            return row[0]

    async def get_ticket_by_channel(self, channel_id):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tickets WHERE channel_id = ?", (channel_id,)
            )
            return await cursor.fetchone()

    async def get_open_ticket_by_user(self, user_id, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tickets WHERE user_id = ? AND guild_id = ? AND status = 'open'",
                (user_id, guild_id),
            )
            return await cursor.fetchone()

    async def close_ticket(self, channel_id, reason, closed_by=None):
        async with aiosqlite.connect(DB_PATH) as db:
            now = datetime.utcnow().isoformat()
            await db.execute("""
                UPDATE tickets SET status='closed', closed_at=?, close_reason=?, owner_id=COALESCE(owner_id, ?)
                WHERE channel_id=?
            """, (now, reason, closed_by, channel_id))
            await db.commit()

    async def set_ticket_owner(self, channel_id, owner_id):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE tickets SET owner_id=? WHERE channel_id=?",
                (owner_id, channel_id),
            )
            await db.commit()

    async def set_ticket_priority(self, channel_id, priority):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE tickets SET priority=? WHERE channel_id=?",
                (priority, channel_id),
            )
            await db.commit()

    async def set_ticket_label(self, channel_id, label):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE tickets SET label=? WHERE channel_id=?",
                (label, channel_id),
            )
            await db.commit()

    async def increment_message_count(self, channel_id):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE tickets SET message_count = message_count + 1 WHERE channel_id=?",
                (channel_id,),
            )
            await db.commit()

    async def add_note(self, ticket_id, author_id, note):
        async with aiosqlite.connect(DB_PATH) as db:
            now = datetime.utcnow().isoformat()
            await db.execute(
                "INSERT INTO ticket_notes (ticket_id, author_id, note, created_at) VALUES (?,?,?,?)",
                (ticket_id, author_id, note, now),
            )
            await db.commit()

    async def get_notes(self, ticket_id):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM ticket_notes WHERE ticket_id=? ORDER BY created_at ASC",
                (ticket_id,),
            )
            return await cursor.fetchall()

    async def add_blacklist(self, user_id, guild_id, added_by, reason):
        async with aiosqlite.connect(DB_PATH) as db:
            now = datetime.utcnow().isoformat()
            await db.execute(
                "INSERT OR REPLACE INTO blacklist (user_id, guild_id, added_by, added_at, reason) VALUES (?,?,?,?,?)",
                (user_id, guild_id, added_by, now, reason),
            )
            await db.commit()

    async def remove_blacklist(self, user_id, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM blacklist WHERE user_id=? AND guild_id=?",
                (user_id, guild_id),
            )
            await db.commit()

    async def is_blacklisted(self, user_id, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT 1 FROM blacklist WHERE user_id=? AND guild_id=?",
                (user_id, guild_id),
            )
            return await cursor.fetchone() is not None

    async def get_blacklist(self, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM blacklist WHERE guild_id=?", (guild_id,)
            )
            return await cursor.fetchall()

    async def save_rating(self, ticket_id, user_id, staff_id, rating):
        async with aiosqlite.connect(DB_PATH) as db:
            now = datetime.utcnow().isoformat()
            await db.execute(
                "INSERT OR REPLACE INTO ratings (ticket_id, user_id, staff_id, rating, created_at) VALUES (?,?,?,?,?)",
                (ticket_id, user_id, staff_id, rating, now),
            )
            await db.commit()

    async def get_stats(self, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            total = (await (await db.execute(
                "SELECT COUNT(*) FROM tickets WHERE guild_id=?", (guild_id,)
            )).fetchone())[0]
            open_count = (await (await db.execute(
                "SELECT COUNT(*) FROM tickets WHERE guild_id=? AND status='open'", (guild_id,)
            )).fetchone())[0]
            today = datetime.utcnow().strftime("%Y-%m-%d")
            today_count = (await (await db.execute(
                "SELECT COUNT(*) FROM tickets WHERE guild_id=? AND created_at LIKE ?",
                (guild_id, f"{today}%"),
            )).fetchone())[0]
            avg_row = await (await db.execute("""
                SELECT AVG((julianday(closed_at) - julianday(created_at)) * 86400)
                FROM tickets WHERE guild_id=? AND status='closed' AND closed_at IS NOT NULL
            """, (guild_id,))).fetchone()
            avg_close = avg_row[0] if avg_row and avg_row[0] else 0
            staff_row = await (await db.execute("""
                SELECT owner_id, COUNT(*) as cnt FROM tickets
                WHERE guild_id=? AND owner_id IS NOT NULL
                GROUP BY owner_id ORDER BY cnt DESC LIMIT 1
            """, (guild_id,))).fetchone()
            cat_row = await (await db.execute("""
                SELECT category, COUNT(*) as cnt FROM tickets
                WHERE guild_id=?
                GROUP BY category ORDER BY cnt DESC LIMIT 1
            """, (guild_id,))).fetchone()
            return {
                "total": total,
                "open": open_count,
                "today": today_count,
                "avg_close": avg_close,
                "top_staff": staff_row[0] if staff_row else None,
                "top_category": cat_row[0] if cat_row else None,
            }

    async def get_rating_report(self, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT r.staff_id, AVG(r.rating) as avg_rating, COUNT(*) as total
                FROM ratings r
                JOIN tickets t ON t.id = r.ticket_id
                WHERE t.guild_id=?
                GROUP BY r.staff_id ORDER BY avg_rating DESC
            """, (guild_id,))
            return await cursor.fetchall()

    async def get_all_open_tickets(self):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tickets WHERE status='open'"
            )
            return await cursor.fetchall()

    async def get_guild_settings(self, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM guild_settings WHERE guild_id=?", (guild_id,)
            )
            return await cursor.fetchone()

    async def save_guild_settings(self, guild_id, **kwargs):
        async with aiosqlite.connect(DB_PATH) as db:
            existing = await (await db.execute(
                "SELECT 1 FROM guild_settings WHERE guild_id=?", (guild_id,)
            )).fetchone()
            if not existing:
                await db.execute(
                    "INSERT INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
                )
            for key, value in kwargs.items():
                await db.execute(
                    f"UPDATE guild_settings SET {key}=? WHERE guild_id=?",
                    (value, guild_id),
                )
            await db.commit()

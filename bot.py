import discord
from discord.ext import commands
from utils.database import Database

COGS = [
    "cogs.tickets",
    "cogs.panel",
    "cogs.logs",
    "cogs.blacklist",
    "cogs.stats",
    "cogs.autoclose",
]


class TicketBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self.db = Database()

    async def setup_hook(self):
        await self.db.initialize()
        for cog in COGS:
            try:
                await self.load_extension(cog)
                print(f"✅ Cog yüklendi: {cog}")
            except Exception as e:
                print(f"❌ Cog yüklenemedi {cog}: {e}")
        await self.tree.sync()
        print("✅ Slash komutları senkronize edildi.")

    async def on_ready(self):
        print(f"✅ Bot hazır: {self.user} ({self.user.id})")
        await self.change_presence(
            activity=discord.Game(name="🎫 Ticket Sistemi | /panel-kur")
        )

import asyncio
import os
import sys
from bot import TicketBot


async def main():
    token = os.environ.get("TOKEN")
    if not token:
        print("HATA: TOKEN ortam değişkeni bulunamadı.")
        sys.exit(1)

    bot = TicketBot()
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())

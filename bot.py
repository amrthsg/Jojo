# bot.py
# نقطه ورود اصلی ربات - ثبت تمام هندلرها و استارت polling

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db

# ⚠️ نکته مهم: تمام روترها باید اینجا import و register بشن
# قبل از asyncio.run(main()) - این باگی بود که تو پروژه قبلیت (Sssdddd) پیدا کردیم!
from handlers.start import router as start_router
from handlers.meow import router as meow_router
from handlers.bank import router as bank_router
from handlers.market import router as market_router
from handlers.leaderboard import router as leaderboard_router
from handlers.admin import router as admin_router
from handlers.games.table_games import router as games_router

logging.basicConfig(level=logging.INFO)


async def main():
    init_db()  # ساخت جداول دیتابیس اگه وجود نداشته باشن

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # ترتیب رجیستر مهمه: اول start، بعد بقیه
    dp.include_router(start_router)
    dp.include_router(admin_router)   # قبل از meow چون /admin باید اول چک بشه
    dp.include_router(bank_router)
    dp.include_router(market_router)
    dp.include_router(leaderboard_router)
    dp.include_router(games_router)
    dp.include_router(meow_router)    # هندلرهای متنی عمومی، آخر بمونه بهتره

    logging.info("ربات جوجو استارت شد ✅")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

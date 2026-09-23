# bot.py
# نقطه ورود اصلی ربات - ثبت تمام هندلرها و استارت polling

import asyncio
import logging
import os
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db
from utils.middleware import DisplayNameMiddleware

# ⚠️ نکته مهم: تمام روترها باید اینجا import و register بشن
# قبل از asyncio.run(main()) - این باگی بود که تو پروژه قبلیت (Sssdddd) پیدا کردیم!
from handlers.start import router as start_router
from handlers.meow import router as meow_router
from handlers.bank import router as bank_router
from handlers.market import router as market_router
from handlers.leaderboard import router as leaderboard_router
from handlers.admin import router as admin_router
from handlers.games.table_games import router as games_router
from handlers.games.casino import router as casino_router
from handlers.factory import router as factory_router
from handlers.city import router as city_router
from handlers.smuggling import router as smuggling_router
from handlers.chance_spawn import router as chance_spawn_router

logging.basicConfig(level=logging.INFO)


async def _health_check(request):
    """
    یه اندپوینت خیلی ساده که فقط برای health-check پلتفرم‌های هاستینگ
    (مثل Orbit/Flux، Railway و مشابه) استفاده میشه - نشون میده پروسه زندهست.
    خود بات همچنان با polling کار میکنه؛ این وبسرور کاری با تلگرام نداره.
    """
    return web.Response(text="jojo bot is running ✅")


async def _start_health_server():
    """
    یه وبسرور سبک روی پورتی که پلتفرم هاستینگ میده (env variable PORT) بالا میاره.
    اگه PORT ست نشده بود (مثلاً روی VPS خودمون)، این وبسرور اصلاً استارت نمیشه
    و فقط پولینگ عادی ادامه پیدا میکنه.
    """
    port_str = os.environ.get("PORT")
    if not port_str:
        return  # روی VPS/لوکال نیازی به وبسرور نیست

    port = int(port_str)
    app = web.Application()
    app.router.add_get("/", _health_check)
    app.router.add_get("/health", _health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"وبسرور health-check روی پورت {port} بالا اومد ✅")


async def main():
    init_db()  # ساخت جداول دیتابیس اگه وجود نداشته باشن

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # میدلور به‌روزرسانی خودکار اسم و یوزرنیم کاربر (برای پروفایل و لیدربرد)
    dp.message.middleware(DisplayNameMiddleware())

    # ترتیب رجیستر مهمه: اول start، بعد بقیه
    dp.include_router(start_router)
    dp.include_router(admin_router)   # قبل از meow چون /admin باید اول چک بشه
    dp.include_router(bank_router)
    dp.include_router(market_router)
    dp.include_router(leaderboard_router)
    dp.include_router(games_router)
    dp.include_router(casino_router)
    dp.include_router(factory_router)
    dp.include_router(city_router)
    dp.include_router(smuggling_router)
    dp.include_router(meow_router)    # هندلرهای متنی عمومی (شامل «غذا» هم میشه)
    # chance_spawn_router باید آخرین باشه: فیلترش (F.text تو گروه) خیلی
    # عمومیه و باید فقط وقتی هیچکدوم از دستورات بالا match نکردن اجرا بشه.
    dp.include_router(chance_spawn_router)

    logging.info("ربات جوجو استارت شد ✅")
    await _start_health_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

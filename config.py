# config.py
# تنظیمات اصلی ربات جوجو

BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"

# آیدی عددی مالک ربات - فقط همین شخص میتونه ادمین اضافه/حذف کنه
OWNER_ID = 5779467403  # امیر

# آیدی عددی ادمین‌های اولیه (نصب اولیه). ادمین‌های بعدی از طریق دستورات
# پویا (/addadmin و /removeadmin) به دیتابیس اضافه/حذف میشن، نه اینجا.
ADMIN_IDS = [
    5779467403,  # امیر
]

DB_PATH = "jojo_bot.db"

# نام جوجو و ارز پیش‌فرض
DEFAULT_PET_NAME = "جوجو"
CURRENCY_NAME = "جیک پوینت"
CURRENCY_EMOJI = "🪙"

# ------- تنظیمات جیک کردن (Core Loop) -------
# کول‌داون پایه به ثانیه (سطح 1) و حداقل کول‌داون (سطح 50 به بالا)
MEOW_COOLDOWN_BASE = 300      # 5:00 دقیقه
MEOW_COOLDOWN_MIN = 240       # 4:00 دقیقه (حداقل، سطح‌های بالا)
MEOW_COOLDOWN_STEP_LEVELS = 3  # هر چند سطح، کول‌داون کم بشه
MEOW_COOLDOWN_STEP_SECONDS = 5  # به چه میزان کم بشه

# حداکثر سطح
MAX_LEVEL = 50

# ظرفیت شکم اولیه و افزایش با ارتقا مقام (rank up هر 5 سطح)
BASE_CAPACITY = 15625
CAPACITY_GROWTH_PER_RANK = 2.0  # هر رنک، ظرفیت 2 برابر میشه (تقریبی)

# ------- بانک -------
BANK_MIN_LEVEL = 4
BANK_DAILY_INTEREST_RATE = 0.03      # 3 درصد روزانه
BANK_DAILY_INTEREST_CAP = 500000     # سقف سود روزانه
BANK_ACCOUNT_OPEN_COST = 5000

CARD_TRANSFER_FEE_PERCENT = 2        # 2 درصد کارمزد
CARD_TRANSFER_MIN_FEE = 100
CARD_TRANSFER_MAX_FEE = 100000
CARD_NUMBER_CHANGE_COST = 1250
CARD_NUMBER_CHANGE_COOLDOWN = 6 * 3600  # هر 6 ساعت یکبار

# وام بانکی
LOAN_MAX_AMOUNT = 5_500_000
LOAN_FEE_PERCENT = 10             # 10 درصد کارمزد روی کل وام
LOAN_INSTALLMENTS_COUNT = 3       # تعداد اقساط
LOAN_INSTALLMENT_INTERVAL_SECONDS = 24 * 3600  # هر قسط، هر 24 ساعت
LOAN_MAX_ACTIVE_PER_USER = 1      # حداکثر تعداد وام فعال همزمان برای هر کاربر

# ------- انتقال جیک پوینت مستقیم (بین کاربرها) -------
TRANSFER_MIN_AMOUNT = 50
TRANSFER_MAX_AMOUNT = 500000
TRANSFER_MIN_LEVEL = 3
TRANSFER_COOLDOWN = 30  # ثانیه بین هر انتقال

# ------- بازی‌های میزی (مینی‌گیم پوینت‌محور) -------
GAMES_MIN_LEVEL = 2
GAMES_TABLE_MIN_LEVEL = 3  # سطح لازم برای ساخت میز بازی
GAME_COOLDOWN = 120         # 2 دقیقه استراحت بین بازی‌ها

# نوع بازی‌های پشتیبانی‌شده با ایموجی دایس تلگرام
GAME_TYPES = {
    "basketball": "🏀",
    "bowling": "🎳",
    "darts": "🎯",
    "football": "⚽",
}

# ------- پنل ادمین -------
ADMIN_GIFT_MAX_AMOUNT = 10_000_000  # حداکثر مقداری که ادمین یکجا هدیه میده

# ------- آیتم شانسی تو گروه (جوجه گمشده / دونه طلایی) -------
CHANCE_SPAWN_MESSAGE_INTERVAL = 50  # بعد از هر ۵۰ پیام تو گروه، شانس ظاهر شدن
CHANCE_SPAWN_EXPIRE_SECONDS = 120   # بعد از ۲ دقیقه اگه کسی نخرید، منقضی میشه

# ------- کازینو چندنفره -------
CASINO_MIN_LEVEL = 4
CASINO_TABLE_MIN_LEVEL = 6
CASINO_MIN_PLAYERS = 2
CASINO_MAX_PLAYERS = 8
CASINO_JOIN_WINDOW_SECONDS = 60  # مدت زمانی که میز باز میمونه تا بقیه بپیوندن

# ------- غذای جوجه (سیستم گرسنگی) -------
HUNGER_INTERVAL_SECONDS = 4 * 3600  # هر 4 ساعت جوجو گرسنه میشه
FEED_COST = 150                      # هزینه‌ی هر بار غذا دادن دستی (بنویس «غذا»)

# ------- کارخونه جوجویی -------
FACTORY_MIN_LEVEL = 7
FACTORY_BASE_STORAGE = 5000
FACTORY_PRODUCTION_TIME_SECONDS = 24  # زمان پایه‌ی تولید هر محصول
FACTORY_UPGRADE_COST = 100_000
FACTORY_WORKER_HIRE_COST = 5_000
FACTORY_MAX_WORKERS = 10

# محصولات قابل تولید در کارخونه: (نام، هزینه تولید، ارزش فروش)
FACTORY_PRODUCTS = {
    "آبنبات": {"cost": 50, "sell_price": 90},
    "شکلات": {"cost": 100, "sell_price": 180},
    "آدامس": {"cost": 30, "sell_price": 55},
}

# ------- شهر جوجویی (گروهی) -------
CITY_MIN_LEVEL_FOR_BUILDING = 7  # سطح شهر لازم برای باز شدن ساختمان شهرداری
CITY_UPGRADE_TREASURY_TARGETS = {
    # سطح شهر: (خزانه موردنیاز, جیک موردنیاز, جمعیت موردنیاز)
    1: {"treasury": 500_000, "jik": 1000, "population": 20},
    2: {"treasury": 1_000_000, "jik": 2500, "population": 40},
    3: {"treasury": 2_500_000, "jik": 5000, "population": 80},
}

# ------- قاچاق جوجه -------
SMUGGLING_MIN_LEVEL = 6
SMUGGLING_MIN_CHICKS = 3
SMUGGLING_MAX_CHICKS = 15
SMUGGLING_DURATION_SECONDS = 300  # 5 دقیقه هر ماموریت
SMUGGLING_CATCH_CHANCE_PER_CHICK = 0.03  # هر جوجه اضافه، ریسک لو رفتن رو زیاد میکنه
SMUGGLING_REWARD_MIN_PER_CHICK = 12_500
SMUGGLING_REWARD_MAX_PER_CHICK = 24_000


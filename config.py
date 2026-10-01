# config.py
# تنظیمات اصلی ربات جوجو

import os

# توکن از environment variable خونده میشه (برای دیپلوی روی Railway یا هر پلتفرم دیگه)
# اگه env variable ست نشده بود، از مقدار پیش‌فرض زیر استفاده میشه (برای اجرای لوکال/VPS)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8488308082:AAFS5-AUN0ik0uRGKtm2WSW_M0WLUEtQ3cE")

# آیدی عددی مالک ربات - فقط همین شخص میتونه ادمین اضافه/حذف کنه
OWNER_ID = int(os.environ.get("OWNER_ID", "5779467403"))  # امیر

# آیدی عددی ادمین‌های اولیه (نصب اولیه). ادمین‌های بعدی از طریق دستورات
# پویا (/addadmin و /removeadmin) به دیتابیس اضافه/حذف میشن، نه اینجا.
ADMIN_IDS = [
    OWNER_ID,  # امیر
]

# مسیر دیتابیس - روی Railway باید به یه Volume وصل بشه (مثلاً /data/jojo_bot.db)
# تا با هر ری‌دیپلوی پاک نشه. اگه env variable ست نشده بود، همینجا کنار کد ذخیره میشه.
DB_PATH = os.environ.get("DB_PATH", "jojo_bot.db")

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
FACTORY_MIN_LEVEL = 7          # حداقل سطح جوجو برای باز شدن کارخونه
FACTORY_MAX_FACTORY_LEVEL = 30  # سقف سطح کارخونه (نمایش به رومی مثل XVII)

FACTORY_BASE_STORAGE = 5000
FACTORY_STORAGE_GROWTH_PER_LEVEL = 5000   # هر سطح انبار، این مقدار به ظرفیت اضافه میشه
FACTORY_STORAGE_UPGRADE_BASE_COST = 250_000
FACTORY_STORAGE_UPGRADE_COST_STEP = 75_000  # هر سطح، هزینه ارتقای بعدی بیشتر میشه

FACTORY_BASE_SEATS = 3
FACTORY_SEATS_GROWTH_PER_LEVEL = 1        # هر ارتقای صندلی، این مقدار صندلی اضافه میشه
FACTORY_SEATS_UPGRADE_BASE_COST = 325_000
FACTORY_SEATS_UPGRADE_COST_STEP = 100_000
FACTORY_WORKER_HIRE_COST = 5_000
FACTORY_WORKER_FIRE_REFUND_RATIO = 0.5     # درصدی از هزینه استخدام که موقع اخراج برمیگرده

FACTORY_BASE_PRODUCTION_SPEED_SECONDS = 30  # زمان پایه تولید هر واحد محصول
FACTORY_DEVICE_SPEED_REDUCTION_PER_LEVEL = 2  # هر ارتقای دستگاه، این مقدار (ثانیه) سریع‌تر میشه
FACTORY_DEVICE_MIN_SPEED_SECONDS = 4         # حداقل زمان تولید (سقف سرعت)
FACTORY_DEVICE_UPGRADE_BASE_COST = 325_000
FACTORY_DEVICE_UPGRADE_COST_STEP = 100_000

# تجربه‌ی لازم برای رسیدن از هر سطح کارخونه به سطح بعدی (سطح: XP لازم)
FACTORY_XP_PER_LEVEL_BASE = 50_000
FACTORY_XP_PER_LEVEL_STEP = 5_000   # هر سطح، XP لازم برای سطح بعدی این مقدار بیشتر میشه

# محصولات قابل تولید در کارخونه: کلید، نام نمایشی، ایموجی، حداقل سطح کارخونه لازم،
# هزینه تولید هر واحد، قیمت فروش هر واحد، و XP کارخونه‌ای که هر واحد تولیدشده میده
FACTORY_PRODUCTS = {
    "candy": {
        "name": "آبنبات", "emoji": "🍬", "min_factory_level": 1,
        "cost": 50, "sell_price": 90, "xp_per_unit": 5,
    },
    "cake": {
        "name": "کیک", "emoji": "🍰", "min_factory_level": 1,
        "cost": 120, "sell_price": 210, "xp_per_unit": 10,
    },
    "tech": {
        "name": "تکنولوژی", "emoji": "💾", "min_factory_level": 10,
        "cost": 800, "sell_price": 1_400, "xp_per_unit": 40,
    },
    "car": {
        "name": "خودرو", "emoji": "🚗", "min_factory_level": 18,
        "cost": 5_000, "sell_price": 8_800, "xp_per_unit": 150,
    },
    "airplane": {
        "name": "هواپیما", "emoji": "✈️", "min_factory_level": 25,
        "cost": 25_000, "sell_price": 44_000, "xp_per_unit": 600,
    },
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

# ------- پروفایل «جوجویی» (شکم، تولید خودکار پوینت، مقام ویژه) -------
JOJOYI_BASE_BELLY_MAX = 8                 # ظرفیت پایه‌ی شکم
JOJOYI_BELLY_DROP_INTERVAL_SECONDS = 900  # هر ۱۵ دقیقه یک واحد از شکم کم میشه
JOJOYI_FEED_COST = 5_000                  # هزینه‌ی «گرفتن کرم»
JOJOYI_FEED_BELLY_RESTORE = 8             # گرفتن کرم چقدر شکم رو پر میکنه

JOJOYI_BASE_PRODUCTION_RATE = 1.0         # پوینت تولیدی در ثانیه (سطح پایه)
JOJOYI_BASE_PRODUCTION_CAPACITY = 5_000   # سقف پوینت جمع‌شده قبل از نیاز به برداشت

# مقام‌های ویژه‌ی جوجویی: (اسم نمایشی, هزینه ارتقا, سقف شکم جدید, سرعت تولید جدید, ظرفیت جدید)
JOJOYI_RANKS = {
    1: {"name": "پنجه برنز", "upgrade_cost": 0, "belly_max": 8, "production_rate": 1.0, "capacity": 5_000},
    2: {"name": "پنجه نقره", "upgrade_cost": 150_000, "belly_max": 10, "production_rate": 2.0, "capacity": 15_000},
    3: {"name": "پنجه طلا", "upgrade_cost": 250_000, "belly_max": 15, "production_rate": 4.5, "capacity": 145_250},
    4: {"name": "پنجه الماس", "upgrade_cost": 500_000, "belly_max": 20, "production_rate": 8.0, "capacity": 400_000},
    5: {"name": "پنجه افسانه‌ای", "upgrade_cost": 1_200_000, "belly_max": 30, "production_rate": 15.0, "capacity": 1_000_000},
}
JOJOYI_MAX_RANK = max(JOJOYI_RANKS.keys())


# database/models.py
# توابع دسترسی به داده‌ها (CRUD) - هر تابع خودش کانکشن باز/بسته میکنه
# تا مدیریت thread-safety ساده بمونه

import time
from database.db import get_connection
from config import DEFAULT_PET_NAME, BASE_CAPACITY


# ---------------- کاربران ----------------

def get_user(user_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row


def create_user_if_not_exists(user_id: int, username: str | None, display_name: str | None = None):
    """
    اگه کاربر تازه‌ست، جوجوی جدید براش می‌سازه.
    خروجی: True اگه تازه ساخته شد، False اگه از قبل بود.
    """
    user = get_user(user_id)
    if user:
        return False

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO users (user_id, username, display_name, pet_name, level, exp,
                            meow_points, capacity, rank_level, last_meow_time)
        VALUES (?, ?, ?, ?, 1, 0, 0, ?, 1, 0)
        """,
        (user_id, username, display_name, DEFAULT_PET_NAME, BASE_CAPACITY),
    )
    conn.commit()
    conn.close()
    return True


def update_display_name(user_id: int, display_name: str, username: str | None = None):
    """
    اسم تلگرام کاربر رو به‌روز میکنه - هر بار کاربر پیامی میفرسته صدا زده میشه
    تا اگه اسمش رو تلگرام عوض کرد، تو دیتابیس هم به‌روز بمونه.
    """
    conn = get_connection()
    if username is not None:
        conn.execute(
            "UPDATE users SET display_name = ?, username = ? WHERE user_id = ?",
            (display_name, username, user_id),
        )
    else:
        conn.execute(
            "UPDATE users SET display_name = ? WHERE user_id = ?",
            (display_name, user_id),
        )
    conn.commit()
    conn.close()


def update_pet_name(user_id: int, new_name: str):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET pet_name = ?, last_name_change = ? WHERE user_id = ?",
        (new_name, int(time.time()), user_id),
    )
    conn.commit()
    conn.close()


def add_meow_points(user_id: int, amount: int):
    """افزایش (یا کاهش، با amount منفی) موجودی کیف پول کاربر"""
    conn = get_connection()
    conn.execute(
        "UPDATE users SET meow_points = meow_points + ? WHERE user_id = ?",
        (amount, user_id),
    )
    conn.commit()
    conn.close()


def set_last_meow_time(user_id: int, ts: int):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET last_meow_time = ? WHERE user_id = ?",
        (ts, user_id),
    )
    conn.commit()
    conn.close()


def add_exp(user_id: int, amount: int = 1):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET exp = exp + ? WHERE user_id = ?",
        (amount, user_id),
    )
    conn.commit()
    conn.close()


def set_level(user_id: int, new_level: int, new_capacity: int, new_rank: int):
    conn = get_connection()
    conn.execute(
        """UPDATE users
           SET level = ?, capacity = ?, rank_level = ?
           WHERE user_id = ?""",
        (new_level, new_capacity, new_rank, user_id),
    )
    conn.commit()
    conn.close()


def set_jailed(user_id: int, jailed: bool):
    """
    زندانی کردن یا آزاد کردن کاربر توسط ادمین.
    برخلاف is_banned (که کلاً ربات رو غیرفعال میکنه)، زندان فقط جیک کردن
    و بازی‌ها رو مسدود میکنه؛ منطق مسدودسازی دقیق تو هندلرها چک میشه.
    """
    conn = get_connection()
    conn.execute(
        "UPDATE users SET is_jailed = ? WHERE user_id = ?",
        (1 if jailed else 0, user_id),
    )
    conn.commit()
    conn.close()


def set_banned(user_id: int, banned: bool):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET is_banned = ? WHERE user_id = ?",
        (1 if banned else 0, user_id),
    )
    conn.commit()
    conn.close()


def get_leaderboard(order_by: str = "meow_points", limit: int = 10):
    """
    order_by میتونه 'meow_points' یا 'exp' یا 'level' باشه
    """
    allowed = {"meow_points", "exp", "level"}
    if order_by not in allowed:
        order_by = "meow_points"

    conn = get_connection()
    rows = conn.execute(
        f"""SELECT user_id, username, display_name, pet_name, level, {order_by} as score
            FROM users
            WHERE is_banned = 0
            ORDER BY {order_by} DESC
            LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def get_total_stats():
    """آمار کلی برای پنل ادمین"""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as total_users, SUM(meow_points) as total_points FROM users"
    ).fetchone()
    conn.close()
    return row


# ---------------- مدیریت ادمین‌های پویا ----------------
# این توابع کاملاً جدا از ADMIN_IDS تو config.py هستن.
# ADMIN_IDS = ادمین‌های اولیه‌ی نصب (ثابت، فقط دستی قابل تغییر).
# جدول admins = ادمین‌هایی که مالک (owner) بعداً از داخل خود ربات اضافه/حذف کرده.

def add_admin(user_id: int, added_by: int):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO admins (user_id, added_by) VALUES (?, ?)",
        (user_id, added_by),
    )
    conn.commit()
    conn.close()


def remove_admin(user_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def is_dynamic_admin(user_id: int) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM admins WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row is not None


def get_all_dynamic_admins():
    conn = get_connection()
    rows = conn.execute(
        "SELECT user_id, added_by, added_at FROM admins ORDER BY added_at DESC"
    ).fetchall()
    conn.close()
    return rows


# ---------------- شمارنده پیام گروه (برای آیتم شانسی) ----------------

def increment_group_message_count(chat_id: int, threshold: int) -> bool:
    """
    شمارنده پیام‌های گروه رو یکی زیاد میکنه. اگه به آستانه (threshold) رسید،
    شمارنده رو صفر میکنه و True برمیگردونه (یعنی وقت ظاهر شدن آیتم شانسیه).
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT message_count FROM group_message_counters WHERE chat_id = ?", (chat_id,)
    ).fetchone()

    if row is None:
        conn.execute(
            "INSERT INTO group_message_counters (chat_id, message_count) VALUES (?, 1)",
            (chat_id,),
        )
        conn.commit()
        conn.close()
        return False

    new_count = row["message_count"] + 1

    if new_count >= threshold:
        conn.execute(
            "UPDATE group_message_counters SET message_count = 0 WHERE chat_id = ?",
            (chat_id,),
        )
        conn.commit()
        conn.close()
        return True

    conn.execute(
        "UPDATE group_message_counters SET message_count = ? WHERE chat_id = ?",
        (new_count, chat_id),
    )
    conn.commit()
    conn.close()
    return False


# ---------------- غذای جوجه ----------------

def feed_pet(user_id: int):
    """جوجو رو سیر میکنه (زمان آخرین غذا رو به الان آپدیت میکنه)"""
    conn = get_connection()
    conn.execute(
        "UPDATE users SET last_fed_time = ? WHERE user_id = ?",
        (int(time.time()), user_id),
    )
    conn.commit()
    conn.close()


def is_pet_hungry(user_id: int, hunger_interval_seconds: int) -> bool:
    """
    چک میکنه آیا جوجو گرسنه‌ست یا نه.
    اگه last_fed_time صفر باشه (هیچوقت غذا نخورده)، گرسنه محسوب نمیشه
    تا کاربرای جدید همون اول گیر نکنن؛ فقط بعد از اولین بار جیک کردن حساب میشه.
    """
    user = get_user(user_id)
    if not user or user["last_fed_time"] == 0:
        return False
    elapsed = int(time.time()) - user["last_fed_time"]
    return elapsed >= hunger_interval_seconds


# ---------------- کارخونه جوجویی ----------------

def get_factory(user_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM factories WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def create_factory_if_not_exists(user_id: int, base_storage: int, base_seats: int, base_speed: int):
    conn = get_connection()
    existing = conn.execute("SELECT 1 FROM factories WHERE user_id = ?", (user_id,)).fetchone()
    if existing:
        conn.close()
        return False
    conn.execute(
        """INSERT INTO factories (user_id, storage_capacity, seats_count, production_speed_seconds)
           VALUES (?, ?, ?, ?)""",
        (user_id, base_storage, base_seats, base_speed),
    )
    conn.commit()
    conn.close()
    return True


def get_factory_storage_items(user_id: int):
    """لیست همه‌ی محصولات موجود تو انبار این کاربر (کلید محصول + مقدار)"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT product_key, amount FROM factory_storage WHERE user_id = ? AND amount > 0",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def get_factory_total_storage_used(user_id: int) -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM factory_storage WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return row["total"]


def start_factory_production(user_id: int, product_key: str, amount: int, start_time: int):
    conn = get_connection()
    conn.execute(
        """UPDATE factories
           SET current_product = ?, production_amount = ?, production_start_time = ?
           WHERE user_id = ?""",
        (product_key, amount, start_time, user_id),
    )
    conn.commit()
    conn.close()


def collect_factory_production(user_id: int, product_key: str, produced_amount: int, xp_gained: int):
    """محصول تولیدشده رو به انبار (به تفکیک محصول) اضافه میکنه، خط تولید رو خالی میکنه و XP میده"""
    conn = get_connection()
    conn.execute(
        """INSERT INTO factory_storage (user_id, product_key, amount)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id, product_key) DO UPDATE SET amount = amount + excluded.amount""",
        (user_id, product_key, produced_amount),
    )
    conn.execute(
        """UPDATE factories
           SET current_product = NULL, production_amount = 0, production_start_time = 0,
               xp = xp + ?
           WHERE user_id = ?""",
        (xp_gained, user_id),
    )
    conn.commit()
    conn.close()


def sell_factory_product(user_id: int, product_key: str, amount_to_sell: int):
    conn = get_connection()
    conn.execute(
        "UPDATE factory_storage SET amount = amount - ? WHERE user_id = ? AND product_key = ?",
        (amount_to_sell, user_id, product_key),
    )
    conn.commit()
    conn.close()


def sell_all_factory_storage(user_id: int):
    """همه‌ی محصولات انبار رو صفر میکنه (بعد از فروش کلی)"""
    conn = get_connection()
    conn.execute("DELETE FROM factory_storage WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def set_factory_level(user_id: int, new_level: int, remaining_xp: int):
    """وقتی XP کافی جمع شد، سطح کارخونه بالا میره و XP اضافی نگه داشته میشه"""
    conn = get_connection()
    conn.execute(
        "UPDATE factories SET level = ?, xp = ? WHERE user_id = ?",
        (new_level, remaining_xp, user_id),
    )
    conn.commit()
    conn.close()


def upgrade_factory_storage(user_id: int, new_storage_level: int, new_capacity: int):
    conn = get_connection()
    conn.execute(
        "UPDATE factories SET storage_level = ?, storage_capacity = ? WHERE user_id = ?",
        (new_storage_level, new_capacity, user_id),
    )
    conn.commit()
    conn.close()


def upgrade_factory_seats(user_id: int, new_seats_level: int, new_seats_count: int):
    conn = get_connection()
    conn.execute(
        "UPDATE factories SET seats_level = ?, seats_count = ? WHERE user_id = ?",
        (new_seats_level, new_seats_count, user_id),
    )
    conn.commit()
    conn.close()


def upgrade_factory_device(user_id: int, new_device_level: int, new_speed_seconds: int):
    conn = get_connection()
    conn.execute(
        "UPDATE factories SET device_level = ?, production_speed_seconds = ? WHERE user_id = ?",
        (new_device_level, new_speed_seconds, user_id),
    )
    conn.commit()
    conn.close()


def hire_factory_worker(user_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE factories SET workers_count = workers_count + 1 WHERE user_id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()


def fire_factory_worker(user_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE factories SET workers_count = MAX(workers_count - 1, 0) WHERE user_id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()


# ---------------- شهر جوجویی (گروهی) ----------------

def get_city(chat_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM cities WHERE chat_id = ?", (chat_id,)).fetchone()
    conn.close()
    return row


def create_city_if_not_exists(chat_id: int):
    conn = get_connection()
    existing = conn.execute("SELECT 1 FROM cities WHERE chat_id = ?", (chat_id,)).fetchone()
    if existing:
        conn.close()
        return False
    conn.execute("INSERT INTO cities (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    conn.close()
    return True


def donate_to_city(chat_id: int, user_id: int, amount: int):
    conn = get_connection()
    conn.execute(
        "UPDATE cities SET treasury = treasury + ? WHERE chat_id = ?", (amount, chat_id)
    )
    conn.execute(
        "INSERT INTO city_donations (chat_id, user_id, amount) VALUES (?, ?, ?)",
        (chat_id, user_id, amount),
    )
    conn.commit()
    conn.close()


def add_city_jik(chat_id: int, amount: int = 1):
    """هر بار عضوی از گروه جیک میکنه، به مجموع جیک شهر اضافه میشه"""
    conn = get_connection()
    conn.execute(
        "UPDATE cities SET total_jik = total_jik + ? WHERE chat_id = ?", (amount, chat_id)
    )
    conn.commit()
    conn.close()


def add_city_population(chat_id: int, amount: int = 1):
    conn = get_connection()
    conn.execute(
        "UPDATE cities SET population = population + ? WHERE chat_id = ?", (amount, chat_id)
    )
    conn.commit()
    conn.close()


def upgrade_city_level(chat_id: int, new_level: int):
    conn = get_connection()
    conn.execute("UPDATE cities SET level = ? WHERE chat_id = ?", (new_level, chat_id))
    conn.commit()
    conn.close()


def get_city_top_donors(chat_id: int, limit: int = 5):
    conn = get_connection()
    rows = conn.execute(
        """SELECT user_id, SUM(amount) as total FROM city_donations
           WHERE chat_id = ? GROUP BY user_id ORDER BY total DESC LIMIT ?""",
        (chat_id, limit),
    ).fetchall()
    conn.close()
    return rows


# ---------------- قاچاق جوجه ----------------

def create_smuggling_run(user_id: int, chick_count: int, reward: int, started_at: int, finishes_at: int):
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO smuggling_runs (user_id, chick_count, reward, started_at, finishes_at)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, chick_count, reward, started_at, finishes_at),
    )
    run_id = cur.lastrowid
    conn.commit()
    conn.close()
    return run_id


def get_active_smuggling_run(user_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM smuggling_runs WHERE user_id = ? AND status = 'in_progress'",
        (user_id,),
    ).fetchone()
    conn.close()
    return row


def get_smuggling_run(run_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM smuggling_runs WHERE id = ?", (run_id,)).fetchone()
    conn.close()
    return row


def finish_smuggling_run(run_id: int, status: str):
    """status: 'success' یا 'caught'"""
    conn = get_connection()
    conn.execute(
        "UPDATE smuggling_runs SET status = ? WHERE id = ?", (status, run_id)
    )
    conn.commit()
    conn.close()


# ---------------- مالکیت پنل‌های شخصی (بانک، کارخونه و ...) ----------------
# برای جلوگیری از اینکه کاربر دیگه‌ای تو گروه، روی دکمه‌های پنل شخصی یکی دیگه کلیک کنه.

def set_panel_owner(chat_id: int, message_id: int, owner_user_id: int):
    conn = get_connection()
    conn.execute(
        """INSERT INTO panel_owners (chat_id, message_id, owner_user_id)
           VALUES (?, ?, ?)
           ON CONFLICT(chat_id, message_id) DO UPDATE SET owner_user_id = excluded.owner_user_id""",
        (chat_id, message_id, owner_user_id),
    )
    conn.commit()
    conn.close()


def get_panel_owner(chat_id: int, message_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT owner_user_id FROM panel_owners WHERE chat_id = ? AND message_id = ?",
        (chat_id, message_id),
    ).fetchone()
    conn.close()
    return row["owner_user_id"] if row else None


def is_panel_owner(chat_id: int, message_id: int, user_id: int) -> bool:
    """
    اگه پیام تو دیتابیس مالک ثبت‌شده نداشت (مثلاً پیام‌های قدیمی قبل این آپدیت)،
    به‌صورت پیش‌فرض اجازه میده - برای جلوگیری از قفل شدن غیرمنتظره‌ی پنل‌های قدیمی.
    """
    owner = get_panel_owner(chat_id, message_id)
    if owner is None:
        return True
    return owner == user_id


# ---------------- پروفایل «جوجویی» (شکم، تولید خودکار پوینت، مقام ویژه) ----------------

def get_jojoyi_stats(user_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM jojoyi_stats WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def create_jojoyi_stats_if_not_exists(user_id: int, belly_max: int, production_rate: float, production_capacity: int):
    conn = get_connection()
    existing = conn.execute("SELECT 1 FROM jojoyi_stats WHERE user_id = ?", (user_id,)).fetchone()
    if existing:
        conn.close()
        return False
    now = int(time.time())
    conn.execute(
        """INSERT INTO jojoyi_stats
           (user_id, belly, belly_max, production_rate, production_capacity,
            last_production_time, last_belly_drop_time)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, belly_max, belly_max, production_rate, production_capacity, now, now),
    )
    conn.commit()
    conn.close()
    return True


def apply_jojoyi_production(user_id: int, belly_drop_interval_seconds: int):
    """
    محاسبه‌ی تولید خودکار پوینت از آخرین باری که چک شده تا الان، و کم شدن شکم با گذر زمان.
    این تابع رو قبل از نمایش پروفایل «جوجویی» صدا بزن تا اعداد به‌روز باشن.
    """
    stats = get_jojoyi_stats(user_id)
    if not stats:
        return

    now = int(time.time())
    elapsed_production = now - stats["last_production_time"]

    if elapsed_production > 0 and stats["belly"] > 0:
        # فقط وقتی شکم سیره (بیشتر از صفر) تولید انجام میشه
        produced = int(elapsed_production * stats["production_rate"])
        if produced > 0:
            new_pending = min(stats["pending_points"] + produced, stats["production_capacity"])
            conn = get_connection()
            conn.execute(
                """UPDATE jojoyi_stats
                   SET pending_points = ?, produced_total = produced_total + ?, last_production_time = ?
                   WHERE user_id = ?""",
                (new_pending, produced, now, user_id),
            )
            conn.commit()
            conn.close()

    # کم شدن شکم با گذر زمان (هر belly_drop_interval_seconds، یک واحد کم میشه)
    elapsed_belly = now - stats["last_belly_drop_time"]
    drops = elapsed_belly // belly_drop_interval_seconds
    if drops > 0 and stats["belly"] > 0:
        new_belly = max(stats["belly"] - drops, 0)
        new_drop_time = stats["last_belly_drop_time"] + drops * belly_drop_interval_seconds
        conn = get_connection()
        conn.execute(
            "UPDATE jojoyi_stats SET belly = ?, last_belly_drop_time = ? WHERE user_id = ?",
            (new_belly, new_drop_time, user_id),
        )
        conn.commit()
        conn.close()


def feed_jojoyi(user_id: int, belly_restore_amount: int):
    """کرم دادن: شکم رو پر میکنه (تا سقف belly_max)"""
    conn = get_connection()
    conn.execute(
        """UPDATE jojoyi_stats
           SET belly = MIN(belly + ?, belly_max), last_belly_drop_time = strftime('%s','now')
           WHERE user_id = ?""",
        (belly_restore_amount, user_id),
    )
    conn.commit()
    conn.close()


def collect_jojoyi_points(user_id: int) -> int:
    """پوینت‌های جمع‌شده رو به موجودی اصلی (meow_points) منتقل میکنه. مقدار منتقل‌شده رو برمیگردونه."""
    stats = get_jojoyi_stats(user_id)
    if not stats or stats["pending_points"] <= 0:
        return 0

    amount = stats["pending_points"]
    conn = get_connection()
    conn.execute("UPDATE jojoyi_stats SET pending_points = 0 WHERE user_id = ?", (user_id,))
    conn.execute("UPDATE users SET meow_points = meow_points + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()
    return amount


def upgrade_jojoyi_rank(user_id: int, new_rank: int, new_belly_max: int, new_production_rate: float, new_capacity: int):
    conn = get_connection()
    conn.execute(
        """UPDATE jojoyi_stats
           SET jojoyi_rank = ?, belly_max = ?, production_rate = ?, production_capacity = ?
           WHERE user_id = ?""",
        (new_rank, new_belly_max, new_production_rate, new_capacity, user_id),
    )
    conn.commit()
    conn.close()


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


def create_factory_if_not_exists(user_id: int, base_storage: int):
    conn = get_connection()
    existing = conn.execute("SELECT 1 FROM factories WHERE user_id = ?", (user_id,)).fetchone()
    if existing:
        conn.close()
        return False
    conn.execute(
        "INSERT INTO factories (user_id, storage_capacity) VALUES (?, ?)",
        (user_id, base_storage),
    )
    conn.commit()
    conn.close()
    return True


def start_factory_production(user_id: int, product_name: str, amount: int, start_time: int):
    conn = get_connection()
    conn.execute(
        """UPDATE factories
           SET current_product = ?, production_amount = ?, production_start_time = ?
           WHERE user_id = ?""",
        (product_name, amount, start_time, user_id),
    )
    conn.commit()
    conn.close()


def collect_factory_production(user_id: int, produced_amount: int):
    """محصول تولیدشده رو به انبار اضافه میکنه و خط تولید رو خالی میکنه"""
    conn = get_connection()
    conn.execute(
        """UPDATE factories
           SET storage_used = storage_used + ?, current_product = NULL,
               production_amount = 0, production_start_time = 0
           WHERE user_id = ?""",
        (produced_amount, user_id),
    )
    conn.commit()
    conn.close()


def sell_factory_storage(user_id: int, amount_to_sell: int):
    conn = get_connection()
    conn.execute(
        "UPDATE factories SET storage_used = storage_used - ? WHERE user_id = ?",
        (amount_to_sell, user_id),
    )
    conn.commit()
    conn.close()


def upgrade_factory_level(user_id: int, new_level: int, new_storage_capacity: int):
    conn = get_connection()
    conn.execute(
        "UPDATE factories SET level = ?, storage_capacity = ? WHERE user_id = ?",
        (new_level, new_storage_capacity, user_id),
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


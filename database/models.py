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


def create_user_if_not_exists(user_id: int, username: str | None):
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
        INSERT INTO users (user_id, username, pet_name, level, exp,
                            meow_points, capacity, rank_level, last_meow_time)
        VALUES (?, ?, ?, 1, 0, 0, ?, 1, 0)
        """,
        (user_id, username, DEFAULT_PET_NAME, BASE_CAPACITY),
    )
    conn.commit()
    conn.close()
    return True


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
        f"""SELECT user_id, username, pet_name, level, {order_by} as score
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

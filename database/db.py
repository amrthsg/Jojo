# database/db.py
# اتصال به دیتابیس SQLite و ساخت جداول

import sqlite3
from config import DB_PATH


def get_connection():
    """
    یک اتصال جدید به دیتابیس برمیگردونه.
    check_same_thread=False چون بات async هست و ممکنه از چند جا کوئری بزنیم.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    ساخت تمام جداول موردنیاز اگه وجود نداشته باشن.
    این تابع موقع استارت ربات یکبار صدا زده میشه.
    """
    conn = get_connection()
    cur = conn.cursor()

    # جدول اصلی کاربران / پیشی‌ها
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            pet_name TEXT DEFAULT 'جوجو',
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,           -- تعداد میو انجام شده (تجمعی)
            meow_points INTEGER DEFAULT 0,   -- موجودی کیف پول (wallet)
            capacity INTEGER DEFAULT 15625,  -- ظرفیت شکم/جیب
            rank_level INTEGER DEFAULT 1,    -- مقام (هر ۵ سطح ارتقا)
            last_meow_time INTEGER DEFAULT 0,   -- unix timestamp
            last_name_change INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT (strftime('%s','now'))
        )
    """)

    # جدول بانک
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bank_accounts (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            card_number TEXT UNIQUE,
            last_interest_time INTEGER DEFAULT 0,
            last_card_change INTEGER DEFAULT 0,
            opened_at INTEGER DEFAULT (strftime('%s','now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # جدول تراکنش‌های بانکی / انتقال پوینت
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user INTEGER,
            to_user INTEGER,
            amount INTEGER,
            fee INTEGER DEFAULT 0,
            tx_type TEXT,   -- 'transfer' | 'card_transfer' | 'bank_deposit' | 'bank_withdraw' | 'admin_gift'
            timestamp INTEGER DEFAULT (strftime('%s','now'))
        )
    """)

    # جدول محصولات مارکت
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            item_type TEXT,     -- 'street_cat' | 'bait' | 'other'
            description TEXT,
            stock INTEGER DEFAULT -1   -- -1 یعنی نامحدود
        )
    """)

    # جدول خرید کاربران از مارکت (برای محدودیت روزانه ۵۰ عدد)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_id INTEGER,
            quantity INTEGER,
            purchase_date TEXT,   -- 'YYYY-MM-DD' برای شمارش سقف روزانه
            timestamp INTEGER DEFAULT (strftime('%s','now'))
        )
    """)

    # جدول بازی‌های میزی (بسکتبال/بولینگ/دارت/فوتبال)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS game_tables (
            table_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            game_type TEXT,          -- basketball / bowling / darts / football
            creator_id INTEGER,
            bet_amount INTEGER,
            status TEXT DEFAULT 'waiting',  -- waiting / active / finished
            created_at INTEGER DEFAULT (strftime('%s','now'))
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS game_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER,
            user_id INTEGER,
            score INTEGER DEFAULT 0,
            FOREIGN KEY (table_id) REFERENCES game_tables(table_id)
        )
    """)

    # لاگ اقدامات ادمین (شفافیت و ردیابی)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            target_user INTEGER,
            amount INTEGER,
            note TEXT,
            timestamp INTEGER DEFAULT (strftime('%s','now'))
        )
    """)

    conn.commit()
    conn.close()

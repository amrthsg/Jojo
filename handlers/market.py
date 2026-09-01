# handlers/market.py
# مارکت جوجو - کاملاً متنی، خرید با تایپ «خرید {نام محصول}»

from datetime import date
from aiogram import Router, F
from aiogram.types import Message

from database.db import get_connection
from database.models import get_user, add_meow_points
from config import CURRENCY_EMOJI

router = Router()

DAILY_PURCHASE_LIMIT = 50


def _seed_default_items():
    """اگه مارکت خالیه، چند تا آیتم پیش‌فرض اضافه کن"""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) as c FROM market_items").fetchone()["c"]
    if count == 0:
        conn.executemany(
            """INSERT INTO market_items (name, price, item_type, description)
               VALUES (?, ?, ?, ?)""",
            [
                ("جوجه گمشده", 500, "stray_chick", "یک جوجه‌ی تنها برای پناه دادن"),
                ("دونه غذای طلایی", 300, "food", "افزایش سرعت جیک کردن برای مدتی"),
            ],
        )
        conn.commit()
    conn.close()


@router.message(F.text == "مارکت")
async def handle_market(message: Message):
    _seed_default_items()

    conn = get_connection()
    items = conn.execute("SELECT * FROM market_items").fetchall()
    conn.close()

    lines = ["🛍 <b>مارکت جوجو</b>\n", "روزانه فقط ۵۰ محصول میتونی بخری.\n"]
    for item in items:
        lines.append(f"• {item['name']} — {item['price']:,} {CURRENCY_EMOJI}")
        lines.append(f"  {item['description']}")
    lines.append("\nبرای خرید بنویس: «خرید {نام محصول}» مثلاً: خرید جوجه گمشده")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text.startswith("خرید "))
async def handle_buy_item(message: Message):
    item_name = message.text.replace("خرید ", "", 1).strip()
    user_id = message.from_user.id
    today = date.today().isoformat()

    conn = get_connection()
    item = conn.execute(
        "SELECT * FROM market_items WHERE name = ?", (item_name,)
    ).fetchone()

    if not item:
        conn.close()
        await message.answer("❌ این محصول تو مارکت پیدا نشد. بنویس «مارکت» تا لیست رو ببینی.")
        return

    # چک محدودیت روزانه
    bought_today = conn.execute(
        """SELECT COALESCE(SUM(quantity), 0) as total FROM market_purchases
           WHERE user_id = ? AND purchase_date = ?""",
        (user_id, today),
    ).fetchone()["total"]

    if bought_today >= DAILY_PURCHASE_LIMIT:
        conn.close()
        await message.answer("❌ سقف خرید روزانه (۵۰ عدد) پر شده!")
        return

    user = get_user(user_id)
    if not user:
        conn.close()
        await message.answer("اول باید /start بزنی 🐤")
        return

    if user["meow_points"] < item["price"]:
        conn.close()
        await message.answer("❌ موجودی کافی نیست.")
        return

    add_meow_points(user_id, -item["price"])
    conn.execute(
        """INSERT INTO market_purchases (user_id, item_id, quantity, purchase_date)
           VALUES (?, ?, 1, ?)""",
        (user_id, item["item_id"], today),
    )
    conn.commit()
    conn.close()

    await message.answer(f"✅ «{item['name']}» خریداری شد!")

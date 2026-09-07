# handlers/market.py
# مارکت جوجو - با دکمه شیشه‌ای، خرید با کلیک روی دکمه محصول

from datetime import date
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database.db import get_connection
from database.models import get_user, add_meow_points
from keyboards.main_kb import market_menu_kb
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
                ("دان جوجه", 150, "chick_food", "غذای روزانه جوجو برای ادامه تولید"),
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
        lines.append(f"• {item['name']} — {item['description']}")

    await message.answer("\n".join(lines), reply_markup=market_menu_kb(items), parse_mode="HTML")


@router.callback_query(F.data.startswith("market_buy_"))
async def cb_buy_item(callback: CallbackQuery):
    item_id = int(callback.data.replace("market_buy_", ""))
    user_id = callback.from_user.id
    today = date.today().isoformat()

    conn = get_connection()
    item = conn.execute(
        "SELECT * FROM market_items WHERE item_id = ?", (item_id,)
    ).fetchone()

    if not item:
        conn.close()
        await callback.answer("❌ این محصول موجود نیست", show_alert=True)
        return

    bought_today = conn.execute(
        """SELECT COALESCE(SUM(quantity), 0) as total FROM market_purchases
           WHERE user_id = ? AND purchase_date = ?""",
        (user_id, today),
    ).fetchone()["total"]

    if bought_today >= DAILY_PURCHASE_LIMIT:
        conn.close()
        await callback.answer("❌ سقف خرید روزانه (۵۰ عدد) پر شده!", show_alert=True)
        return

    user = get_user(user_id)
    if not user:
        conn.close()
        await callback.answer("اول باید /start بزنی 🐤", show_alert=True)
        return

    if user["meow_points"] < item["price"]:
        conn.close()
        await callback.answer("❌ موجودی کافی نیست", show_alert=True)
        return

    add_meow_points(user_id, -item["price"])
    conn.execute(
        """INSERT INTO market_purchases (user_id, item_id, quantity, purchase_date)
           VALUES (?, ?, 1, ?)""",
        (user_id, item_id, today),
    )
    conn.commit()
    conn.close()

    # اگه آیتم خریداری‌شده «دان جوجه» بود، مستقیم به شکم جوجو اضافه کن
    if item["item_type"] == "chick_food":
        from database.models import feed_pet
        feed_pet(user_id)

    await callback.answer(f"✅ {item['name']} خریداری شد!", show_alert=True)

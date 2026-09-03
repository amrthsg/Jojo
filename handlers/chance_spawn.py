# handlers/chance_spawn.py
# سیستم آیتم شانسی تو گروه‌ها: بعد از هر N پیام، یه آیتم مارکت به‌صورت
# تصادفی تو گروه ظاهر میشه با یه دکمه «خرید» که فقط یک نفر میتونه بخره.

import random
import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database.db import get_connection
from database.models import get_user, add_meow_points, increment_group_message_count
from handlers.market import _seed_default_items
from config import CHANCE_SPAWN_MESSAGE_INTERVAL, CHANCE_SPAWN_EXPIRE_SECONDS, CURRENCY_EMOJI

router = Router()


def _chance_buy_kb(spawn_id: int) -> InlineKeyboardMarkup:
    kb = [[InlineKeyboardButton(text="🛒 خرید", callback_data=f"chance_buy_{spawn_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


@router.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def track_group_messages(message: Message):
    """
    این هندلر رو هر پیام متنیِ گروه صدا زده میشه تا شمارشگر رو به‌روز کنه.
    توجه: چون این تو یک روتر جداست که بعد از بقیه روترهای متنی (بانک،
    بازی، ادمین و...) رجیستر میشه، تداخلی با اون‌ها نداره - چون aiogram
    وقتی یک روتر با فیلترش match کنه و handler خودش پیام رو "مصرف" نکنه
    (یعنی exception نندازه)، به روترهای بعدی هم پیام رو میده مگر اینکه
    صریحاً جلوش گرفته بشه. برای اطمینان کامل این روتر آخرین روتر ثبت‌شده است.
    """
    _seed_default_items()

    should_spawn = increment_group_message_count(message.chat.id, CHANCE_SPAWN_MESSAGE_INTERVAL)
    if not should_spawn:
        return

    conn = get_connection()
    items = conn.execute("SELECT * FROM market_items").fetchall()
    conn.close()

    if not items:
        return

    item = random.choice(items)

    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO chance_spawns (chat_id, message_id, item_name, price, status)
           VALUES (?, 0, ?, ?, 'active')""",
        (message.chat.id, item["name"], item["price"]),
    )
    spawn_id = cur.lastrowid
    conn.commit()
    conn.close()

    sent = await message.answer(
        f"✨ یه <b>{item['name']}</b> پیدا شد!\n"
        f"💰 قیمت: {item['price']:,} {CURRENCY_EMOJI}\n\n"
        f"⏳ فقط تا {CHANCE_SPAWN_EXPIRE_SECONDS} ثانیه فرصت داری بخریش!",
        reply_markup=_chance_buy_kb(spawn_id),
        parse_mode="HTML",
    )

    conn = get_connection()
    conn.execute(
        "UPDATE chance_spawns SET message_id = ? WHERE id = ?", (sent.message_id, spawn_id)
    )
    conn.commit()
    conn.close()


@router.callback_query(F.data.startswith("chance_buy_"))
async def handle_chance_buy(callback: CallbackQuery):
    spawn_id = int(callback.data.replace("chance_buy_", ""))
    user_id = callback.from_user.id

    conn = get_connection()
    spawn = conn.execute(
        "SELECT * FROM chance_spawns WHERE id = ?", (spawn_id,)
    ).fetchone()

    if not spawn:
        conn.close()
        await callback.answer("❌ این آیتم پیدا نشد.", show_alert=True)
        return

    if spawn["status"] != "active":
        conn.close()
        await callback.answer("❌ این آیتم قبلاً خریداری یا منقضی شده.", show_alert=True)
        return

    elapsed = int(time.time()) - spawn["created_at"]
    if elapsed > CHANCE_SPAWN_EXPIRE_SECONDS:
        conn.execute("UPDATE chance_spawns SET status = 'expired' WHERE id = ?", (spawn_id,))
        conn.commit()
        conn.close()
        await callback.answer("⏳ وقت این آیتم تموم شده.", show_alert=True)
        try:
            await callback.message.edit_text(f"⌛ {spawn['item_name']} منقضی شد، کسی نخریدش.")
        except Exception:
            pass
        return

    user = get_user(user_id)
    if not user:
        conn.close()
        await callback.answer("اول باید /start بزنی 🐤", show_alert=True)
        return

    if user["meow_points"] < spawn["price"]:
        conn.close()
        await callback.answer("❌ موجودی کافی نداری.", show_alert=True)
        return

    conn.execute(
        "UPDATE chance_spawns SET status = 'bought', bought_by = ? WHERE id = ?",
        (user_id, spawn_id),
    )
    conn.commit()
    conn.close()

    add_meow_points(user_id, -spawn["price"])

    await callback.answer(f"✅ {spawn['item_name']} رو خریدی!", show_alert=True)

    try:
        await callback.message.edit_text(
            f"🎉 <b>{spawn['item_name']}</b> توسط {callback.from_user.full_name} خریداری شد!",
            parse_mode="HTML",
        )
    except Exception:
        pass

# handlers/admin.py
# پنل ادمین: اهدای پوینت، آمار، بن/آنبن، ویرایش کاربر، پیام همگانی

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.models import (
    get_user,
    add_meow_points,
    set_banned,
    set_level,
    get_total_stats,
)
from database.db import get_connection
from keyboards.main_kb import admin_panel_kb
from config import ADMIN_IDS, ADMIN_GIFT_MAX_AMOUNT, CURRENCY_EMOJI

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class AdminStates(StatesGroup):
    waiting_gift_target = State()
    waiting_gift_amount = State()
    waiting_ban_target = State()
    waiting_unban_target = State()
    waiting_broadcast_text = State()


def _log_admin_action(admin_id: int, action: str, target_user: int | None, amount: int, note: str = ""):
    conn = get_connection()
    conn.execute(
        """INSERT INTO admin_logs (admin_id, action, target_user, amount, note)
           VALUES (?, ?, ?, ?, ?)""",
        (admin_id, action, target_user, amount, note),
    )
    conn.commit()
    conn.close()


@router.message(F.text == "/admin")
async def cmd_admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return  # سکوت کامل برای غیرادمین‌ها

    await message.answer(
        "⚙️ <b>پنل مدیریت جوجو</b>",
        reply_markup=admin_panel_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی نداری", show_alert=True)
        return

    stats = get_total_stats()
    text = (
        f"📊 <b>آمار کلی ربات</b>\n\n"
        f"👥 تعداد کاربران: {stats['total_users']:,}\n"
        f"🪙 مجموع پوینت در گردش: {(stats['total_points'] or 0):,}"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_gift")
async def cb_admin_gift(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی نداری", show_alert=True)
        return

    await callback.message.answer(
        "🎁 آیدی عددی یا یوزرنیم کاربر مقصد رو بفرست (یا روی پیامش ریپلای کن و بنویس 'خودش'):"
    )
    await state.set_state(AdminStates.waiting_gift_target)
    await callback.answer()


@router.message(AdminStates.waiting_gift_target)
async def process_gift_target(message: Message, state: FSMContext):
    target_id = None

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif message.text.strip().lstrip("@").isdigit():
        target_id = int(message.text.strip().lstrip("@"))
    else:
        # جستجو بر اساس یوزرنیم داخل دیتابیس
        conn = get_connection()
        row = conn.execute(
            "SELECT user_id FROM users WHERE username = ?",
            (message.text.strip().lstrip("@"),),
        ).fetchone()
        conn.close()
        if row:
            target_id = row["user_id"]

    if not target_id or not get_user(target_id):
        await message.answer("❌ کاربر پیدا نشد.")
        await state.clear()
        return

    await state.update_data(target_id=target_id)
    await message.answer(f"💰 چه مقدار {CURRENCY_EMOJI} میخوای به این کاربر بدی؟")
    await state.set_state(AdminStates.waiting_gift_amount)


@router.message(AdminStates.waiting_gift_amount)
async def process_gift_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ فقط عدد بفرست.")
        return

    amount = int(message.text)
    if amount <= 0 or amount > ADMIN_GIFT_MAX_AMOUNT:
        await message.answer(f"❌ مقدار باید بین ۱ تا {ADMIN_GIFT_MAX_AMOUNT:,} باشد.")
        await state.clear()
        return

    data = await state.get_data()
    target_id = data["target_id"]

    add_meow_points(target_id, amount)
    _log_admin_action(message.from_user.id, "gift", target_id, amount)

    await message.answer(f"✅ {amount:,} {CURRENCY_EMOJI} به کاربر {target_id} داده شد.")

    try:
        await message.bot.send_message(
            target_id,
            f"🎁 ادمین {amount:,} {CURRENCY_EMOJI} به شما هدیه داد!",
        )
    except Exception:
        pass  # کاربر شاید بلاک کرده باشه

    await state.clear()


@router.callback_query(F.data == "admin_ban")
async def cb_admin_ban(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی نداری", show_alert=True)
        return
    await callback.message.answer("🚫 آیدی عددی کاربر برای مسدود کردن رو بفرست:")
    await state.set_state(AdminStates.waiting_ban_target)
    await callback.answer()


@router.message(AdminStates.waiting_ban_target)
async def process_ban(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ فقط آیدی عددی معتبره.")
        await state.clear()
        return

    target_id = int(message.text)
    set_banned(target_id, True)
    _log_admin_action(message.from_user.id, "ban", target_id, 0)
    await message.answer(f"✅ کاربر {target_id} مسدود شد.")
    await state.clear()


@router.callback_query(F.data == "admin_unban")
async def cb_admin_unban(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی نداری", show_alert=True)
        return
    await callback.message.answer("✅ آیدی عددی کاربر برای رفع مسدودیت رو بفرست:")
    await state.set_state(AdminStates.waiting_unban_target)
    await callback.answer()


@router.message(AdminStates.waiting_unban_target)
async def process_unban(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ فقط آیدی عددی معتبره.")
        await state.clear()
        return

    target_id = int(message.text)
    set_banned(target_id, False)
    _log_admin_action(message.from_user.id, "unban", target_id, 0)
    await message.answer(f"✅ مسدودیت کاربر {target_id} برداشته شد.")
    await state.clear()


@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("دسترسی نداری", show_alert=True)
        return
    await callback.message.answer("📢 متن پیام همگانی رو بفرست:")
    await state.set_state(AdminStates.waiting_broadcast_text)
    await callback.answer()


@router.message(AdminStates.waiting_broadcast_text)
async def process_broadcast(message: Message, state: FSMContext):
    conn = get_connection()
    users = conn.execute("SELECT user_id FROM users WHERE is_banned = 0").fetchall()
    conn.close()

    sent, failed = 0, 0
    for user in users:
        try:
            await message.bot.send_message(user["user_id"], message.text)
            sent += 1
        except Exception:
            failed += 1

    _log_admin_action(message.from_user.id, "broadcast", None, 0, note=message.text[:100])
    await message.answer(f"📢 پیام برای {sent} نفر ارسال شد. ({failed} ناموفق)")
    await state.clear()

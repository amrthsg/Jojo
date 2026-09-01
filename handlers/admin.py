# handlers/admin.py
# پنل ادمین - کاملاً متنی، بدون هیچ دکمه‌ای
# همه دستورات با /admin شروع میشن یا با پیشوند فارسی

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.models import (
    get_user,
    add_meow_points,
    set_banned,
    set_jailed,
    set_level,
    get_total_stats,
    add_admin,
    remove_admin,
    is_dynamic_admin,
    get_all_dynamic_admins,
)
from database.db import get_connection
from config import ADMIN_IDS, OWNER_ID, ADMIN_GIFT_MAX_AMOUNT, CURRENCY_EMOJI

router = Router()


def is_admin(user_id: int) -> bool:
    """
    ادمین = یا تو لیست ثابت ADMIN_IDS (نصب اولیه) هست، یا مالک (owner)
    از داخل ربات اضافه‌ش کرده (جدول admins).
    """
    return user_id in ADMIN_IDS or is_dynamic_admin(user_id)


def is_owner(user_id: int) -> bool:
    """فقط مالک اصلی - تنها کسی که میتونه ادمین اضافه/حذف کنه."""
    return user_id == OWNER_ID


def _log_admin_action(admin_id: int, action: str, target_user: int | None, amount: int, note: str = ""):
    conn = get_connection()
    conn.execute(
        """INSERT INTO admin_logs (admin_id, action, target_user, amount, note)
           VALUES (?, ?, ?, ?, ?)""",
        (admin_id, action, target_user, amount, note),
    )
    conn.commit()
    conn.close()


def _admin_help_text(owner: bool) -> str:
    text = (
        "⚙️ <b>پنل مدیریت جوجو</b>\n\n"
        "<b>دستورات:</b>\n"
        "🎁 اهدا {آیدی} {مبلغ} — اهدای پوینت\n"
        "📊 آمار — آمار کلی ربات\n"
        "🚫 بن {آیدی} — مسدود کردن کاربر\n"
        "✅ آنبن {آیدی} — رفع مسدودیت\n"
        "🔒 زندان {آیدی} — زندانی کردن کاربر\n"
        "🔓 آزادی {آیدی} — آزاد کردن از زندان\n"
        "✏️ ویرایش سطح {آیدی} {سطح جدید} — تغییر سطح کاربر\n"
        "✏️ ویرایش موجودی {آیدی} {مبلغ جدید} — تغییر موجودی کاربر\n"
        "📢 همگانی {متن پیام} — ارسال پیام به همه\n"
    )
    if owner:
        text += (
            "\n<b>دستورات مالک:</b>\n"
            "👑 افزودن ادمین {آیدی}\n"
            "👑 حذف ادمین {آیدی}\n"
            "📋 لیست ادمین‌ها\n"
        )
    return text


@router.message(Command("admin"))
async def cmd_admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return  # سکوت کامل برای غیرادمین‌ها

    await message.answer(
        _admin_help_text(owner=is_owner(message.from_user.id)),
        parse_mode="HTML",
    )


@router.message(F.text == "آمار")
async def handle_stats(message: Message):
    if not is_admin(message.from_user.id):
        return

    stats = get_total_stats()
    text = (
        f"📊 <b>آمار کلی ربات</b>\n\n"
        f"👥 تعداد کاربران: {stats['total_users']:,}\n"
        f"🪙 مجموع پوینت در گردش: {(stats['total_points'] or 0):,}"
    )
    await message.answer(text, parse_mode="HTML")


def _resolve_target(message: Message, args: list[str]) -> int | None:
    """
    آیدی کاربر هدف رو یا از ریپلای، یا از اولین آرگومان (آیدی عددی) بدست میاره.
    """
    if message.reply_to_message:
        return message.reply_to_message.from_user.id
    if args and args[0].lstrip("@").isdigit():
        return int(args[0].lstrip("@"))
    return None


@router.message(F.text.startswith("اهدا "))
async def handle_gift(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()[1:]
    target_id = _resolve_target(message, parts)

    # اگه ریپلای بود، مبلغ اولین آرگومانه؛ وگرنه دومین
    amount_str = parts[0] if message.reply_to_message and parts else (parts[1] if len(parts) > 1 else None)

    if not target_id or not amount_str or not amount_str.isdigit():
        await message.answer("❌ فرمت درست: اهدا {آیدی} {مبلغ}  (یا ریپلای کن: اهدا {مبلغ})")
        return

    amount = int(amount_str)
    if amount <= 0 or amount > ADMIN_GIFT_MAX_AMOUNT:
        await message.answer(f"❌ مقدار باید بین ۱ تا {ADMIN_GIFT_MAX_AMOUNT:,} باشد.")
        return

    if not get_user(target_id):
        await message.answer("❌ کاربر پیدا نشد.")
        return

    add_meow_points(target_id, amount)
    _log_admin_action(message.from_user.id, "gift", target_id, amount)
    await message.answer(f"✅ {amount:,} {CURRENCY_EMOJI} به کاربر {target_id} داده شد.")

    try:
        await message.bot.send_message(target_id, f"🎁 ادمین {amount:,} {CURRENCY_EMOJI} به شما هدیه داد!")
    except Exception:
        pass


@router.message(F.text.startswith("بن "))
async def handle_ban(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()[1:]
    target_id = _resolve_target(message, parts)

    if not target_id:
        await message.answer("❌ فرمت درست: بن {آیدی}  (یا ریپلای کن: بن)")
        return

    set_banned(target_id, True)
    _log_admin_action(message.from_user.id, "ban", target_id, 0)
    await message.answer(f"🚫 کاربر {target_id} مسدود شد.")


@router.message(F.text.startswith("آنبن "))
async def handle_unban(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()[1:]
    target_id = _resolve_target(message, parts)

    if not target_id:
        await message.answer("❌ فرمت درست: آنبن {آیدی}  (یا ریپلای کن: آنبن)")
        return

    set_banned(target_id, False)
    _log_admin_action(message.from_user.id, "unban", target_id, 0)
    await message.answer(f"✅ مسدودیت کاربر {target_id} برداشته شد.")


@router.message(F.text.startswith("زندان "))
async def handle_jail(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()[1:]
    target_id = _resolve_target(message, parts)

    if not target_id:
        await message.answer("❌ فرمت درست: زندان {آیدی}  (یا ریپلای کن: زندان)")
        return

    set_jailed(target_id, True)
    _log_admin_action(message.from_user.id, "jail", target_id, 0)
    await message.answer(f"🔒 کاربر {target_id} زندانی شد.")

    try:
        await message.bot.send_message(target_id, "🔒 جوجوت توسط ادمین زندانی شد.")
    except Exception:
        pass


@router.message(F.text.startswith("آزادی "))
async def handle_unjail(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()[1:]
    target_id = _resolve_target(message, parts)

    if not target_id:
        await message.answer("❌ فرمت درست: آزادی {آیدی}  (یا ریپلای کن: آزادی)")
        return

    set_jailed(target_id, False)
    _log_admin_action(message.from_user.id, "unjail", target_id, 0)
    await message.answer(f"🔓 کاربر {target_id} از زندان آزاد شد.")

    try:
        await message.bot.send_message(target_id, "🔓 جوجوت آزاد شد! می‌تونی دوباره جیک جیک کنی.")
    except Exception:
        pass


@router.message(F.text.startswith("ویرایش سطح "))
async def handle_edit_level(message: Message):
    """
    فرمت: ویرایش سطح {آیدی} {سطح جدید}
    یا با ریپلای: ویرایش سطح {سطح جدید}
    """
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()[2:]  # بعد از "ویرایش سطح"
    target_id = _resolve_target(message, parts)

    level_str = parts[0] if message.reply_to_message and parts else (parts[1] if len(parts) > 1 else None)

    if not target_id or not level_str or not level_str.isdigit():
        await message.answer(
            "❌ فرمت درست: ویرایش سطح {آیدی} {سطح جدید}  (یا ریپلای کن: ویرایش سطح {سطح جدید})"
        )
        return

    new_level = int(level_str)
    target_user = get_user(target_id)

    if not target_user:
        await message.answer("❌ کاربر پیدا نشد.")
        return

    from utils.leveling import get_capacity_for_rank
    from config import MAX_LEVEL

    if new_level < 1 or new_level > MAX_LEVEL:
        await message.answer(f"❌ سطح باید بین ۱ تا {MAX_LEVEL} باشد.")
        return

    new_rank = (new_level - 1) // 5 + 1
    new_capacity = get_capacity_for_rank(new_rank)

    set_level(target_id, new_level, new_capacity, new_rank)
    _log_admin_action(message.from_user.id, "edit_level", target_id, new_level)
    await message.answer(f"✅ سطح کاربر {target_id} به {new_level} تغییر کرد.")

    try:
        await message.bot.send_message(target_id, f"⭐ سطح جوجوت توسط ادمین به {new_level} تغییر کرد.")
    except Exception:
        pass


@router.message(F.text.startswith("ویرایش موجودی "))
async def handle_edit_balance(message: Message):
    """
    فرمت: ویرایش موجودی {آیدی} {مبلغ جدید}
    یا با ریپلای: ویرایش موجودی {مبلغ جدید}
    """
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()[2:]  # بعد از "ویرایش موجودی"
    target_id = _resolve_target(message, parts)

    amount_str = parts[0] if message.reply_to_message and parts else (parts[1] if len(parts) > 1 else None)

    if not target_id or not amount_str or not amount_str.isdigit():
        await message.answer(
            "❌ فرمت درست: ویرایش موجودی {آیدی} {مبلغ جدید}  (یا ریپلای کن: ویرایش موجودی {مبلغ})"
        )
        return

    new_balance = int(amount_str)
    target_user = get_user(target_id)

    if not target_user:
        await message.answer("❌ کاربر پیدا نشد.")
        return

    # چون add_meow_points فقط جمع/کم میکنه، اختلاف رو حساب می‌کنیم
    diff = new_balance - target_user["meow_points"]
    add_meow_points(target_id, diff)

    _log_admin_action(message.from_user.id, "edit_balance", target_id, new_balance)
    await message.answer(f"✅ موجودی کاربر {target_id} به {new_balance:,} {CURRENCY_EMOJI} تغییر کرد.")

    try:
        await message.bot.send_message(
            target_id, f"💰 موجودی جوجوت توسط ادمین به {new_balance:,} {CURRENCY_EMOJI} تغییر کرد."
        )
    except Exception:
        pass


@router.message(F.text.startswith("همگانی "))
async def handle_broadcast(message: Message):
    if not is_admin(message.from_user.id):
        return

    text = message.text.replace("همگانی ", "", 1).strip()
    if not text:
        await message.answer("❌ متن پیام خالیه.")
        return

    conn = get_connection()
    users = conn.execute("SELECT user_id FROM users WHERE is_banned = 0").fetchall()
    conn.close()

    sent, failed = 0, 0
    for user in users:
        try:
            await message.bot.send_message(user["user_id"], text)
            sent += 1
        except Exception:
            failed += 1

    _log_admin_action(message.from_user.id, "broadcast", None, 0, note=text[:100])
    await message.answer(f"📢 پیام برای {sent} نفر ارسال شد. ({failed} ناموفق)")


# ---------------- دستورات مخصوص مالک (owner) ----------------

@router.message(F.text.startswith("افزودن ادمین "))
async def handle_add_admin(message: Message):
    if not is_owner(message.from_user.id):
        return  # سکوت کامل حتی برای ادمین‌های عادی

    parts = message.text.split()[2:]
    target_id = _resolve_target(message, parts)

    if not target_id:
        await message.answer("❌ فرمت درست: افزودن ادمین {آیدی}  (یا ریپلای کن: افزودن ادمین)")
        return

    if target_id in ADMIN_IDS or is_dynamic_admin(target_id):
        await message.answer("⚠️ این کاربر از قبل ادمینه.")
        return

    add_admin(target_id, message.from_user.id)
    _log_admin_action(message.from_user.id, "add_admin", target_id, 0)
    await message.answer(f"✅ کاربر {target_id} به عنوان ادمین اضافه شد.")

    try:
        await message.bot.send_message(target_id, "👑 تبریک! شما ادمین ربات جوجو شدید.")
    except Exception:
        pass


@router.message(F.text.startswith("حذف ادمین "))
async def handle_remove_admin(message: Message):
    if not is_owner(message.from_user.id):
        return

    parts = message.text.split()[2:]
    target_id = _resolve_target(message, parts)

    if not target_id:
        await message.answer("❌ فرمت درست: حذف ادمین {آیدی}  (یا ریپلای کن: حذف ادمین)")
        return

    if target_id == OWNER_ID:
        await message.answer("❌ نمیتونی مالک ربات رو حذف کنی.")
        return

    if target_id in ADMIN_IDS:
        await message.answer(
            "⚠️ این کاربر جزو ادمین‌های اولیه (تو config.py) هست و از داخل ربات "
            "قابل حذف نیست. باید مستقیم از فایل config.py رو سرور حذفش کنی."
        )
        return

    if not is_dynamic_admin(target_id):
        await message.answer("⚠️ این کاربر اصلاً ادمین نیست.")
        return

    remove_admin(target_id)
    _log_admin_action(message.from_user.id, "remove_admin", target_id, 0)
    await message.answer(f"✅ کاربر {target_id} از ادمین‌ها حذف شد.")

    try:
        await message.bot.send_message(target_id, "شما دیگر ادمین ربات جوجو نیستید.")
    except Exception:
        pass


@router.message(F.text == "لیست ادمین‌ها")
async def handle_list_admins(message: Message):
    if not is_owner(message.from_user.id):
        return

    dynamic_admins = get_all_dynamic_admins()

    lines = ["👑 <b>لیست ادمین‌های ربات جوجو</b>\n"]
    lines.append("<b>ادمین‌های اولیه (ثابت):</b>")
    for admin_id in ADMIN_IDS:
        owner_tag = " (مالک)" if admin_id == OWNER_ID else ""
        lines.append(f"• <code>{admin_id}</code>{owner_tag}")

    lines.append("\n<b>ادمین‌های افزوده‌شده:</b>")
    if dynamic_admins:
        for admin in dynamic_admins:
            lines.append(f"• <code>{admin['user_id']}</code>")
    else:
        lines.append("هیچکس")

    await message.answer("\n".join(lines), parse_mode="HTML")

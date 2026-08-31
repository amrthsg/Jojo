# keyboards/main_kb.py
# کیبوردهای ثابت ربات

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb() -> ReplyKeyboardMarkup:
    """منوی اصلی که همیشه پایین صفحه هست"""
    kb = [
        [KeyboardButton(text="🐣 جوجو جوجو کن")],
        [KeyboardButton(text="🪙 جوجو پوینت"), KeyboardButton(text="⭐ تجربه و سطح")],
        [KeyboardButton(text="🎮 بازی‌ها"), KeyboardButton(text="🏦 بانک")],
        [KeyboardButton(text="🛍 مارکت"), KeyboardButton(text="🏆 لیدربرد")],
        [KeyboardButton(text="🪪 پروفایل جوجو")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def bank_menu_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="💰 موجودی بانک", callback_data="bank_balance")],
        [InlineKeyboardButton(text="⬆️ واریز", callback_data="bank_deposit"),
         InlineKeyboardButton(text="⬇️ برداشت", callback_data="bank_withdraw")],
        [InlineKeyboardButton(text="💳 انتقال کارت به کارت", callback_data="bank_transfer")],
        [InlineKeyboardButton(text="🔄 تغییر شماره حساب", callback_data="bank_change_number")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def games_menu_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🏀 بسکتبال", callback_data="game_basketball"),
         InlineKeyboardButton(text="🎳 بولینگ", callback_data="game_bowling")],
        [InlineKeyboardButton(text="🎯 دارت", callback_data="game_darts"),
         InlineKeyboardButton(text="⚽ فوتبال", callback_data="game_football")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def leaderboard_menu_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="💰 ثروتمندترین‌ها", callback_data="lb_meow_points")],
        [InlineKeyboardButton(text="🐣 پرسر و صداترین‌ها", callback_data="lb_exp")],
        [InlineKeyboardButton(text="⭐ بالاترین سطح‌ها", callback_data="lb_level")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def admin_panel_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🎁 اهدای پوینت به کاربر", callback_data="admin_gift")],
        [InlineKeyboardButton(text="📊 آمار کلی ربات", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🚫 مسدود کردن کاربر", callback_data="admin_ban")],
        [InlineKeyboardButton(text="✅ رفع مسدودیت", callback_data="admin_unban")],
        [InlineKeyboardButton(text="✏️ ویرایش سطح/موجودی", callback_data="admin_edit_user")],
        [InlineKeyboardButton(text="📢 پیام همگانی", callback_data="admin_broadcast")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def welcome_inline_kb(bot_username: str) -> InlineKeyboardMarkup:
    """
    دکمه‌های زیر پیام معرفی /start.
    دکمه افزودن به گروه با startgroup کاربر رو مستقیم به فلوی افزودن ربات به گروه می‌بره.
    """
    kb = [
        [InlineKeyboardButton(
            text="➕ افزودن من به گروه",
            url=f"https://t.me/{bot_username}?startgroup=true",
        )],
        [InlineKeyboardButton(text="❓ راهنمای کامل", callback_data="show_guide")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def confirm_kb(confirm_data: str, cancel_data: str = "cancel_action") -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="✅ تایید", callback_data=confirm_data),
         InlineKeyboardButton(text="❌ انصراف", callback_data=cancel_data)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

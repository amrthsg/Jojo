# keyboards/main_kb.py
# کیبوردهای ثابت ربات
# توجه: تنها دکمه‌های باقی‌مونده زیر پیام /start هستن (افزودن به گروه، راهنما).
# بانک، بازی‌ها، لیدربرد، ادمین و مارکت همگی کاملاً متنی هستن و هیچ دکمه‌ای ندارن.

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def welcome_inline_kb(bot_username: str) -> InlineKeyboardMarkup:
    """
    دکمه‌های زیر پیام معرفی /start.
    دکمه افزودن به گروه یک لینک خارجی (url) است که کاربر رو مستقیم به فلوی
    افزودن ربات به گروه می‌بره - این یک اکشن تلگرامی است، نه یک منوی داخلی ربات.
    دکمه راهنما هم برای راحتی کاربر نگه داشته شده (معادل تایپ کردن «راهنما»).
    """
    kb = [
        [InlineKeyboardButton(
            text="➕ افزودن من به گروه",
            url=f"https://t.me/{bot_username}?startgroup=true",
        )],
        [InlineKeyboardButton(text="❓ راهنمای کامل", callback_data="show_guide")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

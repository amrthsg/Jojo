# keyboards/main_kb.py
# کیبوردهای ثابت ربات
#
# قانون فعلی پروژه:
# - بانک، مارکت، لیدربرد و بازی‌ها (بسکتبال/بولینگ/دارت/فوتبال/کازینو) دکمه شیشه‌ای دارن.
# - پنل ادمین هم دکمه شیشه‌ای دارد.
# - جیک جیک کردن، پروفایل، سطح، انتقال جیک و امثال این‌ها همچنان کاملاً متنی هستن.

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def welcome_inline_kb(bot_username: str) -> InlineKeyboardMarkup:
    """دکمه‌های زیر پیام معرفی /start."""
    kb = [
        [InlineKeyboardButton(
            text="➕ افزودن من به گروه",
            url=f"https://t.me/{bot_username}?startgroup=true",
        )],
        [InlineKeyboardButton(text="❓ راهنمای کامل", callback_data="show_guide")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def bank_menu_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="💳 کارت به کارت", callback_data="bank_transfer")],
        [InlineKeyboardButton(text="⬆️ واریز", callback_data="bank_deposit"),
         InlineKeyboardButton(text="⬇️ برداشت", callback_data="bank_withdraw")],
        [InlineKeyboardButton(text="➕ درخواست وام", callback_data="bank_loan_request"),
         InlineKeyboardButton(text="📜 تراکنش‌ها", callback_data="bank_transactions")],
        [InlineKeyboardButton(text="🔄 تغییر شماره حساب", callback_data="bank_change_number")],
        [InlineKeyboardButton(text="🔒 قفل بانک", callback_data="bank_lock")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def bank_percent_kb(action: str) -> InlineKeyboardMarkup:
    """
    دکمه‌های سریع درصدی برای واریز/برداشت (action = 'deposit' یا 'withdraw').
    """
    kb = [
        [InlineKeyboardButton(text="۲۵٪", callback_data=f"bankpct_{action}_25"),
         InlineKeyboardButton(text="۵۰٪", callback_data=f"bankpct_{action}_50")],
        [InlineKeyboardButton(text="۷۵٪", callback_data=f"bankpct_{action}_75"),
         InlineKeyboardButton(text="✅ ۱۰۰٪", callback_data=f"bankpct_{action}_100")],
        [InlineKeyboardButton(text="✏️ مبلغ دلخواه", callback_data=f"bankpct_{action}_custom")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="bank_balance")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def bank_transfer_percent_kb() -> InlineKeyboardMarkup:
    """دکمه‌های درصدی برای مرحله‌ی انتخاب مبلغ انتقال کارت‌به‌کارت"""
    kb = [
        [InlineKeyboardButton(text="۲۵٪", callback_data="transferpct_25"),
         InlineKeyboardButton(text="۵۰٪", callback_data="transferpct_50")],
        [InlineKeyboardButton(text="۷۵٪", callback_data="transferpct_75"),
         InlineKeyboardButton(text="✅ ۱۰۰٪", callback_data="transferpct_100")],
        [InlineKeyboardButton(text="✏️ مبلغ دلخواه", callback_data="transferpct_custom")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def bank_lock_confirm_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="❌ لغو", callback_data="bank_lock_cancel"),
         InlineKeyboardButton(text="✅ تایید", callback_data="bank_lock_confirm")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def market_menu_kb(items) -> InlineKeyboardMarkup:
    """
    items: لیست ردیف‌های market_items از دیتابیس
    """
    kb = []
    for item in items:
        kb.append([InlineKeyboardButton(
            text=f"{item['name']} — {item['price']:,} 🪙",
            callback_data=f"market_buy_{item['item_id']}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def games_menu_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🏀 بسکتبال", callback_data="game_basketball"),
         InlineKeyboardButton(text="🎳 بولینگ", callback_data="game_bowling")],
        [InlineKeyboardButton(text="🎯 دارت", callback_data="game_darts"),
         InlineKeyboardButton(text="⚽ فوتبال", callback_data="game_football")],
        [InlineKeyboardButton(text="🎰 کازینو", callback_data="game_casino")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def bet_amount_kb(game_type: str) -> InlineKeyboardMarkup:
    """دکمه‌های انتخاب سریع مبلغ شرط برای یک بازی مشخص"""
    amounts = [100, 500, 1000, 5000]
    kb = [[InlineKeyboardButton(text=f"{a:,}", callback_data=f"bet_{game_type}_{a}")] for a in amounts]
    kb.append([InlineKeyboardButton(text="✏️ مبلغ دلخواه", callback_data=f"bet_custom_{game_type}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def leaderboard_menu_kb() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="💰 ثروتمندترین‌ها", callback_data="lb_meow_points")],
        [InlineKeyboardButton(text="🐤 پرفعالیت‌ترین‌ها", callback_data="lb_exp")],
        [InlineKeyboardButton(text="⭐ بالاترین سطح‌ها", callback_data="lb_level")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def admin_panel_kb(is_owner: bool = False) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🎁 اهدای پوینت", callback_data="admin_gift"),
         InlineKeyboardButton(text="➖ کاهش موجودی", callback_data="admin_reduce")],
        [InlineKeyboardButton(text="📊 آمار کلی ربات", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🚫 مسدود کردن", callback_data="admin_ban"),
         InlineKeyboardButton(text="✅ رفع مسدودیت", callback_data="admin_unban")],
        [InlineKeyboardButton(text="🔒 زندانی کردن", callback_data="admin_jail"),
         InlineKeyboardButton(text="🔓 آزاد کردن", callback_data="admin_unjail")],
        [InlineKeyboardButton(text="✏️ ویرایش سطح", callback_data="admin_edit_level"),
         InlineKeyboardButton(text="✏️ ویرایش موجودی", callback_data="admin_edit_balance")],
        [InlineKeyboardButton(text="📢 پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🎁 اهدا به همه", callback_data="admin_gift_all")],
    ]
    if is_owner:
        kb.append([InlineKeyboardButton(text="👑 افزودن ادمین", callback_data="owner_add_admin")])
        kb.append([InlineKeyboardButton(text="👑 حذف ادمین", callback_data="owner_remove_admin")])
        kb.append([InlineKeyboardButton(text="📋 لیست ادمین‌ها", callback_data="owner_list_admins")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_fsm")]])

# handlers/games/casino.py
# بازی کازینو چندنفره: چند نفر شرط می‌بندن، یک نفر تصادفی (متناسب با شانس/برابر) برنده میشه
# کاملاً دکمه‌ای (شیشه‌ای) - از ساخت میز تا انتخاب مبلغ شرط.

import asyncio
import random
import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.models import get_user, add_meow_points
from database.db import get_connection
from keyboards.main_kb import casino_menu_kb, casino_bet_amount_kb, casino_join_kb, cancel_kb
from config import (
    CASINO_MIN_LEVEL,
    CASINO_TABLE_MIN_LEVEL,
    CASINO_MIN_PLAYERS,
    CASINO_MAX_PLAYERS,
    CASINO_JOIN_WINDOW_SECONDS,
    CURRENCY_EMOJI,
)

router = Router()


class CasinoStates(StatesGroup):
    waiting_custom_bet = State()


def _casino_intro_text() -> str:
    return (
        "🎰 <b>کازینو جوجو</b>\n\n"
        f"بین {CASINO_MIN_PLAYERS} تا {CASINO_MAX_PLAYERS} نفر میتونن با هم شرط ببندن.\n"
        f"همه پول رو وسط میذارن، یک نفر تصادفی همه رو میبره!"
    )


@router.message(F.text == "کازینو")
async def handle_casino_menu(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("اول باید /start بزنی 🐤")
        return

    if user["is_jailed"]:
        await message.answer("🔒 جوجوت زندانیه، نمی‌تونی بازی کنی.")
        return

    if user["level"] < CASINO_MIN_LEVEL:
        await message.answer(f"🎰 برای بازی کازینو باید حداقل سطح {CASINO_MIN_LEVEL} باشی.")
        return

    await message.answer(_casino_intro_text(), reply_markup=casino_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "casino_create")
async def cb_casino_create(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("اول باید /start بزنی 🐤", show_alert=True)
        return

    if user["is_jailed"]:
        await callback.answer("🔒 جوجوت زندانیه، نمی‌تونی بازی کنی.", show_alert=True)
        return

    if user["level"] < CASINO_TABLE_MIN_LEVEL:
        await callback.answer(f"❌ برای ساخت میز کازینو باید حداقل سطح {CASINO_TABLE_MIN_LEVEL} باشی.", show_alert=True)
        return

    await callback.message.edit_text(
        "🎰 <b>مبلغ شرط رو انتخاب کن</b>",
        reply_markup=casino_bet_amount_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "casino_back")
async def cb_casino_back(callback: CallbackQuery):
    await callback.message.edit_text(_casino_intro_text(), reply_markup=casino_menu_kb(), parse_mode="HTML")
    await callback.answer()


async def _create_casino_table(bot, chat_id: int, user_id: int, amount: int):
    """میز کازینو رو می‌سازه و شمارش معکوس رو شروع می‌کنه. مقدار برگشتی: (table_id, error_text)"""
    user = get_user(user_id)
    if not user or amount <= 0 or amount > user["meow_points"]:
        return None, "❌ موجودی کافی نیست."

    add_meow_points(user_id, -amount)

    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO casino_tables (chat_id, creator_id, bet_amount, status)
           VALUES (?, ?, ?, 'waiting')""",
        (chat_id, user_id, amount),
    )
    table_id = cur.lastrowid
    conn.execute(
        "INSERT INTO casino_players (table_id, user_id) VALUES (?, ?)",
        (table_id, user_id),
    )
    conn.commit()
    conn.close()

    return table_id, None


@router.callback_query(F.data.startswith("casinobet_") & ~F.data.endswith("custom"))
async def cb_casino_bet_amount(callback: CallbackQuery):
    amount = int(callback.data.replace("casinobet_", ""))
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    table_id, error = await _create_casino_table(callback.bot, chat_id, user_id, amount)
    if error:
        await callback.answer(error, show_alert=True)
        return

    await callback.answer("✅ میز کازینو ساخته شد!", show_alert=True)
    await callback.message.edit_text(
        f"🎰 میز کازینو #{table_id} با شرط {amount:,} {CURRENCY_EMOJI} باز شد!\n"
        f"👥 بازیکنان: 1 نفر\n"
        f"⏳ {CASINO_JOIN_WINDOW_SECONDS} ثانیه فرصت برای پیوستن بقیه.\n\n"
        f"حداقل {CASINO_MIN_PLAYERS} نفر لازمه تا بازی شروع بشه.",
        reply_markup=casino_join_kb(table_id),
    )

    asyncio.create_task(
        _resolve_casino_after_delay(callback.bot, table_id, chat_id, callback.message.message_id)
    )


@router.callback_query(F.data == "casinobet_custom")
async def cb_casino_bet_custom(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CasinoStates.waiting_custom_bet)
    await state.update_data(chat_id=callback.message.chat.id)
    await callback.message.edit_text(
        "✏️ عدد مبلغ شرط رو بفرست (مثلاً 2000 یا 5k):",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(CasinoStates.waiting_custom_bet)
async def handle_custom_bet_amount(message: Message, state: FSMContext):
    from utils.amount_parser import parse_amount

    amount = parse_amount(message.text.strip())
    if amount is None or amount <= 0:
        await message.answer("❌ مبلغ نامعتبره. یه عدد بفرست، مثلاً 2000 یا 5k")
        return

    data = await state.get_data()
    chat_id = data.get("chat_id")
    await state.clear()

    table_id, error = await _create_casino_table(message.bot, chat_id, message.from_user.id, amount)
    if error:
        await message.answer(error)
        return

    sent = await message.answer(
        f"🎰 میز کازینو #{table_id} با شرط {amount:,} {CURRENCY_EMOJI} باز شد!\n"
        f"👥 بازیکنان: 1 نفر\n"
        f"⏳ {CASINO_JOIN_WINDOW_SECONDS} ثانیه فرصت برای پیوستن بقیه.\n\n"
        f"حداقل {CASINO_MIN_PLAYERS} نفر لازمه تا بازی شروع بشه.",
        reply_markup=casino_join_kb(table_id),
    )

    asyncio.create_task(
        _resolve_casino_after_delay(message.bot, table_id, sent.chat.id, sent.message_id)
    )


async def _resolve_casino_after_delay(bot, table_id: int, chat_id: int, message_id: int):
    await asyncio.sleep(CASINO_JOIN_WINDOW_SECONDS)
    await _finish_casino_table(bot, table_id, chat_id, message_id)


async def _finish_casino_table(bot, table_id: int, chat_id: int, message_id: int):
    conn = get_connection()
    table = conn.execute(
        "SELECT * FROM casino_tables WHERE table_id = ? AND status = 'waiting'", (table_id,)
    ).fetchone()

    if not table:
        conn.close()
        return  # قبلاً تموم شده

    players = conn.execute(
        "SELECT * FROM casino_players WHERE table_id = ?", (table_id,)
    ).fetchall()

    if len(players) < CASINO_MIN_PLAYERS:
        # بازی کنسل میشه، پول‌ها برمیگردن
        for p in players:
            add_meow_points(p["user_id"], table["bet_amount"])
        conn.execute("UPDATE casino_tables SET status = 'finished' WHERE table_id = ?", (table_id,))
        conn.commit()
        conn.close()
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"❌ میز کازینو #{table_id} به دلیل کمبود بازیکن کنسل شد. پول‌ها برگشت داده شد.",
            )
        except Exception:
            pass
        return

    winner = random.choice(players)
    total_pot = table["bet_amount"] * len(players)

    add_meow_points(winner["user_id"], total_pot)
    conn.execute(
        "UPDATE casino_tables SET status = 'finished', winner_id = ? WHERE table_id = ?",
        (winner["user_id"], table_id),
    )
    conn.commit()
    conn.close()

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                f"🎰 میز کازینو #{table_id} تموم شد!\n"
                f"👥 {len(players)} نفر شرکت کردن\n"
                f"🏆 برنده: کاربر {winner['user_id']}\n"
                f"💰 جایزه: {total_pot:,} {CURRENCY_EMOJI}"
            ),
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("casino_join_"))
async def handle_casino_join(callback: CallbackQuery):
    table_id = int(callback.data.replace("casino_join_", ""))
    user_id = callback.from_user.id

    conn = get_connection()
    table = conn.execute(
        "SELECT * FROM casino_tables WHERE table_id = ? AND status = 'waiting'", (table_id,)
    ).fetchone()

    if not table:
        conn.close()
        await callback.answer("❌ این میز دیگه فعال نیست.", show_alert=True)
        return

    already_joined = conn.execute(
        "SELECT 1 FROM casino_players WHERE table_id = ? AND user_id = ?", (table_id, user_id)
    ).fetchone()

    if already_joined:
        conn.close()
        await callback.answer("⚠️ قبلاً به این میز پیوستی.", show_alert=True)
        return

    current_count = conn.execute(
        "SELECT COUNT(*) as c FROM casino_players WHERE table_id = ?", (table_id,)
    ).fetchone()["c"]

    if current_count >= CASINO_MAX_PLAYERS:
        conn.close()
        await callback.answer("❌ این میز پره.", show_alert=True)
        return

    user = get_user(user_id)
    if not user or user["meow_points"] < table["bet_amount"]:
        conn.close()
        await callback.answer("❌ موجودی کافی نداری.", show_alert=True)
        return

    if user["is_jailed"]:
        conn.close()
        await callback.answer("🔒 جوجوت زندانیه، نمی‌تونی بازی کنی.", show_alert=True)
        return

    add_meow_points(user_id, -table["bet_amount"])
    conn.execute(
        "INSERT INTO casino_players (table_id, user_id) VALUES (?, ?)", (table_id, user_id)
    )
    conn.commit()

    new_count = current_count + 1
    conn.close()

    await callback.answer("✅ به میز پیوستی!", show_alert=True)

    try:
        await callback.message.edit_text(
            f"🎰 میز کازینو #{table_id} با شرط {table['bet_amount']:,} {CURRENCY_EMOJI} باز شد!\n"
            f"👥 بازیکنان: {new_count} نفر\n"
            f"⏳ منتظر بقیه یا پایان زمان...",
            reply_markup=casino_join_kb(table_id),
        )
    except Exception:
        pass

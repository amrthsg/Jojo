# handlers/smuggling.py
# قاچاق جوجه - ماموریت زمان‌دار با ریسک لو رفتن، با دکمه شیشه‌ای
# هرچی جوجه بیشتر قاچاق کنی، جایزه بیشتره ولی ریسک لو رفتن هم بیشتره.

import asyncio
import random
import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database.models import (
    get_user,
    add_meow_points,
    create_smuggling_run,
    get_active_smuggling_run,
    get_smuggling_run,
    finish_smuggling_run,
)
from keyboards.main_kb import smuggling_menu_kb, smuggling_chick_count_kb
from utils.leveling import format_time
from config import (
    SMUGGLING_MIN_LEVEL,
    SMUGGLING_MIN_CHICKS,
    SMUGGLING_MAX_CHICKS,
    SMUGGLING_DURATION_SECONDS,
    SMUGGLING_CATCH_CHANCE_PER_CHICK,
    SMUGGLING_REWARD_MIN_PER_CHICK,
    SMUGGLING_REWARD_MAX_PER_CHICK,
    CURRENCY_EMOJI,
)

router = Router()


def _run_status_text(run) -> str:
    if not run:
        return (
            "🚚 <b>قاچاق جوجه</b>\n\n"
            f"می‌تونی بین {SMUGGLING_MIN_CHICKS} تا {SMUGGLING_MAX_CHICKS} جوجه رو قاچاق کنی.\n"
            "هرچی جوجه بیشتر ببری، جایزه بیشتره، ولی احتمال لو رفتن هم بالاتر میره!"
        )

    now = int(time.time())
    if now >= run["finishes_at"]:
        return "🚚 ماموریتت تموم شده! نتیجه رو بررسی کن."

    remaining = run["finishes_at"] - now
    return (
        "🚚 <b>ماموریت در حال انجام</b>\n\n"
        f"🐤 تعداد جوجه: {run['chick_count']}\n"
        f"⏳ زمان باقی‌مانده: {format_time(remaining)}"
    )


@router.message(F.text == "قاچاق")
async def handle_smuggling_menu(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("اول باید /start بزنی 🐤")
        return

    if user["level"] < SMUGGLING_MIN_LEVEL:
        await message.answer(f"🚚 برای قاچاق باید حداقل سطح {SMUGGLING_MIN_LEVEL} باشی.")
        return

    if user["is_jailed"]:
        await message.answer("🔒 جوجوت زندانیه، نمی‌تونی قاچاق کنی.")
        return

    run = get_active_smuggling_run(message.from_user.id)

    await message.answer(
        _run_status_text(run),
        reply_markup=smuggling_menu_kb(has_active_run=bool(run)),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "smuggling_start")
async def cb_smuggling_start(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or user["level"] < SMUGGLING_MIN_LEVEL:
        await callback.answer(f"❌ برای قاچاق باید حداقل سطح {SMUGGLING_MIN_LEVEL} باشی.", show_alert=True)
        return

    if get_active_smuggling_run(callback.from_user.id):
        await callback.answer("⚠️ یه ماموریت در حال انجامه.", show_alert=True)
        return

    await callback.message.edit_text(
        "🚚 <b>چند تا جوجه ببریم؟</b>\n\nهرچی بیشتر، جایزه بیشتر ولی ریسک لو رفتن هم بیشتر!",
        reply_markup=smuggling_chick_count_kb(SMUGGLING_MIN_CHICKS, SMUGGLING_MAX_CHICKS),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("smuggle_go_"))
async def cb_smuggling_go(callback: CallbackQuery):
    chick_count = int(callback.data.replace("smuggle_go_", ""))
    user_id = callback.from_user.id

    if get_active_smuggling_run(user_id):
        await callback.answer("⚠️ یه ماموریت در حال انجامه.", show_alert=True)
        return

    reward = chick_count * random.randint(SMUGGLING_REWARD_MIN_PER_CHICK, SMUGGLING_REWARD_MAX_PER_CHICK)
    now = int(time.time())
    finishes_at = now + SMUGGLING_DURATION_SECONDS

    run_id = create_smuggling_run(user_id, chick_count, reward, now, finishes_at)

    await callback.answer("🚚 ماموریت شروع شد! منتظر بمون...", show_alert=True)
    await callback.message.edit_text(
        f"🚚 <b>ماموریت در حال انجام</b>\n\n"
        f"🐤 تعداد جوجه: {chick_count}\n"
        f"⏳ زمان باقی‌مانده: {format_time(SMUGGLING_DURATION_SECONDS)}",
        reply_markup=smuggling_menu_kb(has_active_run=True),
        parse_mode="HTML",
    )

    asyncio.create_task(
        _resolve_smuggling_after_delay(
            callback.bot, run_id, user_id, chick_count, reward,
            callback.message.chat.id, callback.message.message_id,
        )
    )


async def _resolve_smuggling_after_delay(bot, run_id, user_id, chick_count, reward, chat_id, message_id):
    await asyncio.sleep(SMUGGLING_DURATION_SECONDS)

    # احتمال لو رفتن: هر جوجه اضافه، ریسک بیشتر (سقف ۹۰٪ تا کاملاً غیرممکن نشه)
    catch_chance = min(chick_count * SMUGGLING_CATCH_CHANCE_PER_CHICK, 0.9)
    caught = random.random() < catch_chance

    if caught:
        finish_smuggling_run(run_id, "caught")
        text = (
            f"🚨 <b>لو رفتی!</b>\n\n"
            f"🐤 {chick_count} جوجه رو نگهبانا گرفتن.\n"
            f"❌ هیچ جایزه‌ای نگرفتی."
        )
    else:
        finish_smuggling_run(run_id, "success")
        add_meow_points(user_id, reward)
        text = (
            f"✅ <b>ماموریت موفق!</b>\n\n"
            f"🐤 {chick_count} جوجه رو سالم قاچاق کردی.\n"
            f"💰 جایزه: {reward:,} {CURRENCY_EMOJI}"
        )

    try:
        await bot.send_message(user_id, text, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data == "smuggling_status")
async def cb_smuggling_status(callback: CallbackQuery):
    run = get_active_smuggling_run(callback.from_user.id)
    await callback.message.edit_text(
        _run_status_text(run),
        reply_markup=smuggling_menu_kb(has_active_run=bool(run)),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "smuggling_back")
async def cb_smuggling_back(callback: CallbackQuery):
    run = get_active_smuggling_run(callback.from_user.id)
    await callback.message.edit_text(
        _run_status_text(run),
        reply_markup=smuggling_menu_kb(has_active_run=bool(run)),
        parse_mode="HTML",
    )
    await callback.answer()

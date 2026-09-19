# handlers/city.py
# شهر جوجویی (سطح گروه) - با دکمه شیشه‌ای
# هر گروه یک شهر داره؛ اعضا با کمک به خزانه و جیک کردن، شهر رو ارتقا میدن.

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.models import (
    get_user,
    add_meow_points,
    get_city,
    create_city_if_not_exists,
    donate_to_city,
    upgrade_city_level,
    get_city_top_donors,
)
from keyboards.main_kb import city_menu_kb, city_donate_amount_kb, cancel_kb
from config import CITY_MIN_LEVEL_FOR_BUILDING, CITY_UPGRADE_TREASURY_TARGETS, CURRENCY_EMOJI

router = Router()


class CityStates(StatesGroup):
    waiting_custom_donation = State()


def _city_status_text(city) -> str:
    lines = [
        "🏙 <b>شهر جوجویی</b>\n",
        f"📈 سطح شهر: {city['level']}",
        f"💰 خزانه: {city['treasury']:,} {CURRENCY_EMOJI}",
        f"🐤 مجموع جیک شهر: {city['total_jik']:,}",
        f"👥 جمعیت: {city['population']:,}",
    ]

    target = CITY_UPGRADE_TREASURY_TARGETS.get(city["level"])
    if target:
        lines.append(
            f"\n🎯 <b>هدف ارتقا به سطح {city['level'] + 1}:</b>\n"
            f"💰 خزانه: {city['treasury']:,} / {target['treasury']:,}\n"
            f"🐤 جیک: {city['total_jik']:,} / {target['jik']:,}\n"
            f"👥 جمعیت: {city['population']:,} / {target['population']:,}"
        )
    else:
        lines.append("\n🏆 شهر به بالاترین سطح تعریف‌شده رسیده!")

    return "\n".join(lines)


@router.message(F.text == "شهر")
async def handle_city_menu(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("🏙 شهر جوجویی فقط تو گروه‌ها فعاله.")
        return

    create_city_if_not_exists(message.chat.id)
    city = get_city(message.chat.id)

    await message.answer(
        _city_status_text(city),
        reply_markup=city_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "city_donate")
async def cb_city_donate(callback: CallbackQuery):
    await callback.message.edit_text(
        "💰 <b>کمک به خزانه شهر</b>\n\nچقدر می‌خوای کمک کنی؟",
        reply_markup=city_donate_amount_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("citydonate_") & ~F.data.endswith("custom"))
async def cb_city_donate_amount(callback: CallbackQuery):
    amount = int(callback.data.replace("citydonate_", ""))
    user = get_user(callback.from_user.id)

    if not user:
        await callback.answer("اول باید /start بزنی 🐤", show_alert=True)
        return

    if user["meow_points"] < amount:
        await callback.answer("❌ موجودی کافی نیست.", show_alert=True)
        return

    add_meow_points(callback.from_user.id, -amount)
    donate_to_city(callback.message.chat.id, callback.from_user.id, amount)

    city = get_city(callback.message.chat.id)
    await callback.answer(f"✅ {amount:,} {CURRENCY_EMOJI} به خزانه شهر کمک کردی!", show_alert=True)
    await callback.message.edit_text(
        _city_status_text(city),
        reply_markup=city_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "citydonate_custom")
async def cb_city_donate_custom(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CityStates.waiting_custom_donation)
    await state.update_data(chat_id=callback.message.chat.id)
    await callback.message.edit_text(
        "✏️ عدد مبلغی که می‌خوای کمک کنی رو بفرست (مثلاً 2000 یا 5k):",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(CityStates.waiting_custom_donation)
async def handle_custom_donation_amount(message: Message, state: FSMContext):
    from utils.amount_parser import parse_amount

    amount = parse_amount(message.text.strip())
    if amount is None or amount <= 0:
        await message.answer("❌ مبلغ نامعتبره. یه عدد بفرست، مثلاً 2000 یا 5k")
        return

    user = get_user(message.from_user.id)
    if not user or user["meow_points"] < amount:
        await message.answer("❌ موجودی کافی نیست.")
        await state.clear()
        return

    data = await state.get_data()
    chat_id = data.get("chat_id")
    await state.clear()

    add_meow_points(message.from_user.id, -amount)
    donate_to_city(chat_id, message.from_user.id, amount)

    city = get_city(chat_id)
    await message.answer(
        f"✅ {amount:,} {CURRENCY_EMOJI} به خزانه شهر کمک کردی!\n\n" + _city_status_text(city),
        reply_markup=city_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "city_upgrade")
async def cb_city_upgrade(callback: CallbackQuery):
    city = get_city(callback.message.chat.id)
    if not city:
        await callback.answer("❌ این گروه هنوز شهر نداره.", show_alert=True)
        return

    target = CITY_UPGRADE_TREASURY_TARGETS.get(city["level"])
    if not target:
        await callback.answer("🏆 شهر از قبل به بالاترین سطح رسیده.", show_alert=True)
        return

    if (
        city["treasury"] < target["treasury"]
        or city["total_jik"] < target["jik"]
        or city["population"] < target["population"]
    ):
        await callback.answer("❌ هنوز شرایط ارتقا کامل نشده. به هدف‌ها نگاه کن.", show_alert=True)
        return

    new_level = city["level"] + 1
    upgrade_city_level(callback.message.chat.id, new_level)

    city = get_city(callback.message.chat.id)
    await callback.answer(f"🎉 شهر به سطح {new_level} ارتقا یافت!", show_alert=True)
    await callback.message.edit_text(
        _city_status_text(city),
        reply_markup=city_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "city_top_donors")
async def cb_city_top_donors(callback: CallbackQuery):
    donors = get_city_top_donors(callback.message.chat.id, limit=5)

    lines = ["🏅 <b>برترین کمک‌کننده‌های شهر</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    if not donors:
        lines.append("هنوز کسی کمکی نکرده.")
    else:
        for i, donor in enumerate(donors):
            medal = medals[i] if i < 3 else f"{i + 1}."
            lines.append(f"{medal} کاربر {donor['user_id']} — {donor['total']:,} {CURRENCY_EMOJI}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=city_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "city_back")
async def cb_city_back(callback: CallbackQuery):
    city = get_city(callback.message.chat.id)
    await callback.message.edit_text(
        _city_status_text(city),
        reply_markup=city_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()

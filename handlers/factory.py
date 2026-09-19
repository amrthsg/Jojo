# handlers/factory.py
# کارخونه جوجویی - با دکمه شیشه‌ای
# جریان: ساخت کارخونه -> انتخاب محصول -> شروع تولید -> صبر -> برداشت -> فروش انبار
# استخدام کارگر سرعت تولید رو تو آینده میشه بهش وصل کرد؛ فعلاً فقط ذخیره میشه.

import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database.models import (
    get_user,
    add_meow_points,
    get_factory,
    create_factory_if_not_exists,
    start_factory_production,
    collect_factory_production,
    sell_factory_storage,
    upgrade_factory_level,
    hire_factory_worker,
)
from keyboards.main_kb import factory_menu_kb, factory_products_kb
from utils.leveling import format_time
from config import (
    FACTORY_MIN_LEVEL,
    FACTORY_BASE_STORAGE,
    FACTORY_PRODUCTION_TIME_SECONDS,
    FACTORY_UPGRADE_COST,
    FACTORY_WORKER_HIRE_COST,
    FACTORY_MAX_WORKERS,
    FACTORY_PRODUCTS,
    CURRENCY_EMOJI,
)

router = Router()


def _production_time_for(workers_count: int) -> int:
    """هر کارگر ۵٪ از زمان تولید کم میکنه (حداقل ۲۰٪ زمان پایه)"""
    reduction = 1 - min(workers_count * 0.05, 0.8)
    return max(int(FACTORY_PRODUCTION_TIME_SECONDS * reduction), int(FACTORY_PRODUCTION_TIME_SECONDS * 0.2))


def _is_production_ready(factory) -> bool:
    if not factory["current_product"]:
        return False
    elapsed = int(time.time()) - factory["production_start_time"]
    needed = _production_time_for(factory["workers_count"])
    return elapsed >= needed


def _factory_status_text(user, factory) -> str:
    if not factory:
        return (
            "🏭 <b>کارخونه جوجویی</b>\n\n"
            f"هنوز کارخونه نساختی. برای شروع، سطح {FACTORY_MIN_LEVEL} لازمه.\n"
            "با ساخت کارخونه میتونی محصول تولید کنی و بفروشی."
        )

    lines = [
        "🏭 <b>کارخونه جوجویی</b>\n",
        f"📈 سطح کارخونه: {factory['level']}",
        f"👷 کارگران: {factory['workers_count']} / {FACTORY_MAX_WORKERS}",
        f"📦 انبار: {factory['storage_used']:,} / {factory['storage_capacity']:,}",
    ]

    if factory["current_product"]:
        if _is_production_ready(factory):
            lines.append(f"\n✅ تولید «{factory['current_product']}» آماده‌ست! برداشت کن.")
        else:
            elapsed = int(time.time()) - factory["production_start_time"]
            needed = _production_time_for(factory["workers_count"])
            remaining = needed - elapsed
            lines.append(f"\n⚙️ در حال تولید «{factory['current_product']}»...")
            lines.append(f"⏳ زمان باقی‌مانده: {format_time(remaining)}")
    else:
        lines.append("\n💤 خط تولید خالیه. یه محصول انتخاب کن و تولید رو شروع کن.")

    return "\n".join(lines)


@router.message(F.text == "کارخونه")
async def handle_factory_menu(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("اول باید /start بزنی 🐤")
        return

    if user["level"] < FACTORY_MIN_LEVEL:
        await message.answer(f"🏭 برای دسترسی به کارخونه باید حداقل سطح {FACTORY_MIN_LEVEL} باشی.")
        return

    factory = get_factory(message.from_user.id)
    is_producing = bool(factory and _is_production_ready(factory))

    await message.answer(
        _factory_status_text(user, factory),
        reply_markup=factory_menu_kb(has_factory=bool(factory), is_producing=is_producing),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "factory_create")
async def cb_factory_create(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or user["level"] < FACTORY_MIN_LEVEL:
        await callback.answer(f"❌ برای ساخت کارخونه باید حداقل سطح {FACTORY_MIN_LEVEL} باشی.", show_alert=True)
        return

    created = create_factory_if_not_exists(callback.from_user.id, FACTORY_BASE_STORAGE)
    if not created:
        await callback.answer("⚠️ از قبل کارخونه داری.", show_alert=True)
        return

    factory = get_factory(callback.from_user.id)
    await callback.answer("✅ کارخونه‌ت ساخته شد!", show_alert=True)
    await callback.message.edit_text(
        _factory_status_text(user, factory),
        reply_markup=factory_menu_kb(has_factory=True, is_producing=False),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "factory_produce")
async def cb_factory_produce(callback: CallbackQuery):
    factory = get_factory(callback.from_user.id)
    if not factory:
        await callback.answer("❌ اول باید کارخونه بسازی.", show_alert=True)
        return

    if factory["current_product"]:
        await callback.answer("⚠️ یه تولید در حال انجامه. اول تمومش کن.", show_alert=True)
        return

    await callback.message.edit_text(
        "⚙️ <b>انتخاب محصول تولیدی</b>\n\nکدوم محصول رو تولید کنیم؟",
        reply_markup=factory_products_kb(FACTORY_PRODUCTS),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("factory_makeprod_"))
async def cb_factory_make_product(callback: CallbackQuery):
    product_name = callback.data.replace("factory_makeprod_", "")
    product = FACTORY_PRODUCTS.get(product_name)
    if not product:
        await callback.answer("❌ محصول نامعتبره.", show_alert=True)
        return

    user = get_user(callback.from_user.id)
    factory = get_factory(callback.from_user.id)
    if not factory:
        await callback.answer("❌ اول باید کارخونه بسازی.", show_alert=True)
        return

    if factory["current_product"]:
        await callback.answer("⚠️ یه تولید در حال انجامه.", show_alert=True)
        return

    # مقدار تولید بر اساس سطح کارخونه (هر سطح، ۱۰ واحد بیشتر)
    amount = 20 + factory["level"] * 10
    total_cost = product["cost"] * amount

    if user["meow_points"] < total_cost:
        await callback.answer(f"❌ برای این تولید {total_cost:,} {CURRENCY_EMOJI} نیاز داری.", show_alert=True)
        return

    free_space = factory["storage_capacity"] - factory["storage_used"]
    if amount > free_space:
        await callback.answer("❌ انبارت جا نداره، اول بفروش یا ارتقا بده.", show_alert=True)
        return

    add_meow_points(callback.from_user.id, -total_cost)
    start_factory_production(callback.from_user.id, product_name, amount, int(time.time()))

    factory = get_factory(callback.from_user.id)
    await callback.answer(f"✅ تولید {amount} عدد «{product_name}» شروع شد!", show_alert=True)
    await callback.message.edit_text(
        _factory_status_text(user, factory),
        reply_markup=factory_menu_kb(has_factory=True, is_producing=False),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "factory_collect")
async def cb_factory_collect(callback: CallbackQuery):
    factory = get_factory(callback.from_user.id)
    if not factory or not factory["current_product"]:
        await callback.answer("❌ چیزی برای برداشت نیست.", show_alert=True)
        return

    if not _is_production_ready(factory):
        await callback.answer("⏳ تولید هنوز آماده نیست.", show_alert=True)
        return

    produced = factory["production_amount"]
    product_name = factory["current_product"]
    collect_factory_production(callback.from_user.id, produced)

    user = get_user(callback.from_user.id)
    factory = get_factory(callback.from_user.id)
    await callback.answer(f"📦 {produced} عدد «{product_name}» به انبار اضافه شد!", show_alert=True)
    await callback.message.edit_text(
        _factory_status_text(user, factory),
        reply_markup=factory_menu_kb(has_factory=True, is_producing=False),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "factory_sell")
async def cb_factory_sell(callback: CallbackQuery):
    factory = get_factory(callback.from_user.id)
    if not factory or factory["storage_used"] <= 0:
        await callback.answer("❌ انبارت خالیه.", show_alert=True)
        return

    # چون تو انبار فعلاً نام محصول تفکیک نمیشه، فروش بر اساس آخرین محصول تولیدشده حساب میشه
    last_product = factory["current_product"] or next(iter(FACTORY_PRODUCTS))
    sell_price = FACTORY_PRODUCTS.get(last_product, next(iter(FACTORY_PRODUCTS.values())))["sell_price"]

    amount_to_sell = factory["storage_used"]
    total_revenue = amount_to_sell * sell_price

    sell_factory_storage(callback.from_user.id, amount_to_sell)
    add_meow_points(callback.from_user.id, total_revenue)

    user = get_user(callback.from_user.id)
    factory = get_factory(callback.from_user.id)
    await callback.answer(f"💰 {amount_to_sell} عدد فروخته شد؛ {total_revenue:,} {CURRENCY_EMOJI} گرفتی!", show_alert=True)
    await callback.message.edit_text(
        _factory_status_text(user, factory),
        reply_markup=factory_menu_kb(has_factory=True, is_producing=False),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "factory_hire")
async def cb_factory_hire(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    factory = get_factory(callback.from_user.id)
    if not factory:
        await callback.answer("❌ اول باید کارخونه بسازی.", show_alert=True)
        return

    if factory["workers_count"] >= FACTORY_MAX_WORKERS:
        await callback.answer("❌ ظرفیت کارگر تکمیله.", show_alert=True)
        return

    if user["meow_points"] < FACTORY_WORKER_HIRE_COST:
        await callback.answer(f"❌ برای استخدام {FACTORY_WORKER_HIRE_COST:,} {CURRENCY_EMOJI} نیاز داری.", show_alert=True)
        return

    add_meow_points(callback.from_user.id, -FACTORY_WORKER_HIRE_COST)
    hire_factory_worker(callback.from_user.id)

    user = get_user(callback.from_user.id)
    factory = get_factory(callback.from_user.id)
    is_producing = bool(factory["current_product"] and _is_production_ready(factory))
    await callback.answer("✅ یه کارگر جدید استخدام شد! سرعت تولید بیشتر شد.", show_alert=True)
    await callback.message.edit_text(
        _factory_status_text(user, factory),
        reply_markup=factory_menu_kb(has_factory=True, is_producing=is_producing),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "factory_upgrade")
async def cb_factory_upgrade(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    factory = get_factory(callback.from_user.id)
    if not factory:
        await callback.answer("❌ اول باید کارخونه بسازی.", show_alert=True)
        return

    cost = FACTORY_UPGRADE_COST * factory["level"]
    if user["meow_points"] < cost:
        await callback.answer(f"❌ برای ارتقا {cost:,} {CURRENCY_EMOJI} نیاز داری.", show_alert=True)
        return

    new_level = factory["level"] + 1
    new_capacity = factory["storage_capacity"] + FACTORY_BASE_STORAGE

    add_meow_points(callback.from_user.id, -cost)
    upgrade_factory_level(callback.from_user.id, new_level, new_capacity)

    user = get_user(callback.from_user.id)
    factory = get_factory(callback.from_user.id)
    is_producing = bool(factory["current_product"] and _is_production_ready(factory))
    await callback.answer(f"⬆️ کارخونه به سطح {new_level} ارتقا یافت!", show_alert=True)
    await callback.message.edit_text(
        _factory_status_text(user, factory),
        reply_markup=factory_menu_kb(has_factory=True, is_producing=is_producing),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "factory_back")
async def cb_factory_back(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    factory = get_factory(callback.from_user.id)
    is_producing = bool(factory and factory["current_product"] and _is_production_ready(factory))
    await callback.message.edit_text(
        _factory_status_text(user, factory),
        reply_markup=factory_menu_kb(has_factory=bool(factory), is_producing=is_producing),
        parse_mode="HTML",
    )
    await callback.answer()

# handlers/factory.py
# کارخونه جوجویی - نسخه کامل با دسته‌بندی محصول، انبار جدا، صندلی کارگران و دستگاه تولید
# جریان: ساخت کارخونه -> انتخاب محصول -> شروع تولید -> صبر -> برداشت -> فروش انبار
# مالکیت پنل چک میشه تا فقط صاحب پنل بتونه روی دکمه‌هاش کلیک کنه.

import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database.models import (
    get_user,
    add_meow_points,
    get_factory,
    create_factory_if_not_exists,
    get_factory_storage_items,
    get_factory_total_storage_used,
    start_factory_production,
    collect_factory_production,
    sell_factory_product,
    sell_all_factory_storage,
    set_factory_level,
    upgrade_factory_storage,
    upgrade_factory_seats,
    upgrade_factory_device,
    hire_factory_worker,
    fire_factory_worker,
    set_panel_owner,
    is_panel_owner,
)
from keyboards.main_kb import (
    factory_menu_kb,
    factory_products_kb,
    factory_storage_kb,
    factory_workers_kb,
    factory_devices_kb,
)
from utils.leveling import format_time, to_roman
from utils.premium_emoji import build_premium_entities, get_fallback
from config import (
    FACTORY_MIN_LEVEL,
    FACTORY_MAX_FACTORY_LEVEL,
    FACTORY_BASE_STORAGE,
    FACTORY_STORAGE_GROWTH_PER_LEVEL,
    FACTORY_STORAGE_UPGRADE_BASE_COST,
    FACTORY_STORAGE_UPGRADE_COST_STEP,
    FACTORY_BASE_SEATS,
    FACTORY_SEATS_GROWTH_PER_LEVEL,
    FACTORY_SEATS_UPGRADE_BASE_COST,
    FACTORY_SEATS_UPGRADE_COST_STEP,
    FACTORY_WORKER_HIRE_COST,
    FACTORY_WORKER_FIRE_REFUND_RATIO,
    FACTORY_BASE_PRODUCTION_SPEED_SECONDS,
    FACTORY_DEVICE_SPEED_REDUCTION_PER_LEVEL,
    FACTORY_DEVICE_MIN_SPEED_SECONDS,
    FACTORY_DEVICE_UPGRADE_BASE_COST,
    FACTORY_DEVICE_UPGRADE_COST_STEP,
    FACTORY_XP_PER_LEVEL_BASE,
    FACTORY_XP_PER_LEVEL_STEP,
    FACTORY_PRODUCTS,
    CURRENCY_EMOJI,
)

router = Router()


# ---------------- محاسبات کمکی ----------------

def _xp_needed_for_level(level: int) -> int:
    return FACTORY_XP_PER_LEVEL_BASE + (level - 1) * FACTORY_XP_PER_LEVEL_STEP


def _storage_upgrade_cost(storage_level: int) -> int:
    return FACTORY_STORAGE_UPGRADE_BASE_COST + (storage_level - 1) * FACTORY_STORAGE_UPGRADE_COST_STEP


def _seats_upgrade_cost(seats_level: int) -> int:
    return FACTORY_SEATS_UPGRADE_BASE_COST + (seats_level - 1) * FACTORY_SEATS_UPGRADE_COST_STEP


def _device_upgrade_cost(device_level: int) -> int:
    return FACTORY_DEVICE_UPGRADE_BASE_COST + (device_level - 1) * FACTORY_DEVICE_UPGRADE_COST_STEP


def _next_device_speed(current_speed: int) -> int:
    return max(current_speed - FACTORY_DEVICE_SPEED_REDUCTION_PER_LEVEL, FACTORY_DEVICE_MIN_SPEED_SECONDS)


def _is_production_ready(factory) -> bool:
    if not factory["current_product"]:
        return False
    elapsed = int(time.time()) - factory["production_start_time"]
    return elapsed >= factory["production_speed_seconds"]


async def _guard_owner(callback: CallbackQuery) -> bool:
    owner_ok = is_panel_owner(callback.message.chat.id, callback.message.message_id, callback.from_user.id)
    if not owner_ok:
        await callback.answer("⛔️ این پنل برای شما نیست جوجو 🐤", show_alert=True)
        return False
    return True


# ---------------- ساخت متن‌ها با ایموجی پرمیوم ----------------

def _factory_main_text(user, factory):
    if not factory:
        text = (
            "🏭 کارخونه جوجویی\n\n"
            f"هنوز کارخونه نساختی. برای شروع، سطح {FACTORY_MIN_LEVEL} لازمه.\n"
            "با ساخت کارخونه میتونی محصول تولید کنی و بفروشی."
        )
        return build_premium_entities(text, [("🏭", "factory")])

    level_roman = to_roman(factory["level"])
    xp_needed = _xp_needed_for_level(factory["level"])
    storage_used = get_factory_total_storage_used(user["user_id"])

    lines = [
        "🏭 کارخونه جوجویی",
        "",
        f"مدیر کارخونه : {user['display_name'] or user['pet_name']} 🐱",
        "",
        "انبار کارخونه 🧳",
        f"ظرفیت انبار : {storage_used:,} / {factory['storage_capacity']:,} محصول ⭐",
        f"سطح : {factory['storage_level']} ⭐",
        "",
        "کارگران کارخونه 🐱",
        f"تعداد کارگران : {factory['workers_count']} / {factory['seats_count']} پیشی 🐱",
        f"سطح : {factory['seats_level']} ⭐",
        "",
        "دستگاه‌های تولید 🖨",
        f"زمان تولید محصول : {factory['production_speed_seconds']} ثانیه ⏳",
        f"سطح : {factory['device_level']} ⭐",
        "",
        f"سطح کارخونه : {level_roman} 🌟",
        f"{factory['xp']:,}XP / {xp_needed:,}XP ⚡️",
    ]

    if factory["current_product"]:
        product = FACTORY_PRODUCTS.get(factory["current_product"])
        if _is_production_ready(factory):
            lines.append(f"\n✅ تولید «{product['name']}» آماده‌ست! برداشت کن.")
        else:
            elapsed = int(time.time()) - factory["production_start_time"]
            remaining = factory["production_speed_seconds"] - elapsed
            lines.append(f"\n⚙️ در حال تولید «{product['name']}»...")
            lines.append(f"⏳ زمان باقی‌مانده: {format_time(remaining)}")
    else:
        lines.append("\nشما درحال مدیریت کارخانه خود میباشید. 📋")

    text = "\n".join(lines)
    placeholders = [
        ("🏭", "factory"), ("🐱", "worker"), ("🧳", "storage"), ("⭐", "star"),
        ("🖨", "gear"), ("⏳", "clock"), ("🌟", "star2"), ("⚡️", "xp"),
    ]
    return build_premium_entities(text, placeholders)


# ---------------- منوی اصلی ----------------

@router.message(F.text.in_({"کارخونه", "کارخونه جوجویی", "کار خونه جوجویی"}))
async def handle_factory_menu(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("اول باید /start بزنی 🐤")
        return

    if user["level"] < FACTORY_MIN_LEVEL:
        await message.answer(f"🏭 برای دسترسی به کارخونه باید حداقل سطح {FACTORY_MIN_LEVEL} باشی.")
        return

    factory = get_factory(message.from_user.id)
    is_ready = bool(factory and _is_production_ready(factory))

    text, entities = _factory_main_text(user, factory)
    sent = await message.answer(
        text, entities=entities or None,
        reply_markup=factory_menu_kb(has_factory=bool(factory), is_producing_ready=is_ready),
    )
    set_panel_owner(sent.chat.id, sent.message_id, message.from_user.id)


async def _refresh_factory_panel(callback: CallbackQuery, user_id: int):
    user = get_user(user_id)
    factory = get_factory(user_id)
    is_ready = bool(factory and _is_production_ready(factory))
    text, entities = _factory_main_text(user, factory)
    await callback.message.edit_text(
        text, entities=entities or None,
        reply_markup=factory_menu_kb(has_factory=bool(factory), is_producing_ready=is_ready),
    )


@router.callback_query(F.data == "factory_back")
async def cb_factory_back(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return
    await _refresh_factory_panel(callback, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "factory_create")
async def cb_factory_create(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return
    user = get_user(callback.from_user.id)
    if not user or user["level"] < FACTORY_MIN_LEVEL:
        await callback.answer(f"❌ برای ساخت کارخونه باید حداقل سطح {FACTORY_MIN_LEVEL} باشی.", show_alert=True)
        return

    created = create_factory_if_not_exists(
        callback.from_user.id, FACTORY_BASE_STORAGE, FACTORY_BASE_SEATS, FACTORY_BASE_PRODUCTION_SPEED_SECONDS
    )
    if not created:
        await callback.answer("⚠️ از قبل کارخونه داری.", show_alert=True)
        return

    await callback.answer("✅ کارخونه‌ت ساخته شد!", show_alert=True)
    await _refresh_factory_panel(callback, callback.from_user.id)


# ---------------- تولید ----------------

@router.callback_query(F.data == "factory_produce")
async def cb_factory_produce(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return
    factory = get_factory(callback.from_user.id)
    if not factory:
        await callback.answer("❌ اول باید کارخونه بسازی.", show_alert=True)
        return
    if factory["current_product"]:
        await callback.answer("⚠️ یه تولید در حال انجامه. اول تمومش کن.", show_alert=True)
        return

    text = "محصولی را جهت شروع تولید انتخاب کنید.. ⬇️"
    text, entities = build_premium_entities(text, [])
    await callback.message.edit_text(
        text, entities=entities or None,
        reply_markup=factory_products_kb(FACTORY_PRODUCTS, factory["level"]),
    )
    await callback.answer()


@router.callback_query(F.data == "factory_locked_product")
async def cb_factory_locked_product(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return
    await callback.answer("🔒 هنوز سطح کارخونه‌ت برای این محصول کافی نیست.", show_alert=True)


@router.callback_query(F.data.startswith("factory_makeprod_"))
async def cb_factory_make_product(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return
    product_key = callback.data.replace("factory_makeprod_", "")
    product = FACTORY_PRODUCTS.get(product_key)
    if not product:
        await callback.answer("❌ محصول نامعتبره.", show_alert=True)
        return

    user = get_user(callback.from_user.id)
    factory = get_factory(callback.from_user.id)
    if not factory:
        await callback.answer("❌ اول باید کارخونه بسازی.", show_alert=True)
        return
    if factory["level"] < product["min_factory_level"]:
        await callback.answer(f"🔒 برای این محصول سطح کارخونه {product['min_factory_level']} لازمه.", show_alert=True)
        return
    if factory["current_product"]:
        await callback.answer("⚠️ یه تولید در حال انجامه.", show_alert=True)
        return

    # مقدار تولید بر اساس تعداد کارگران فعلی (هر کارگر یه واحد اضافه)
    amount = max(factory["workers_count"], 1)
    total_cost = product["cost"] * amount

    if user["meow_points"] < total_cost:
        await callback.answer(f"❌ برای این تولید {total_cost:,} {CURRENCY_EMOJI} نیاز داری.", show_alert=True)
        return

    storage_used = get_factory_total_storage_used(callback.from_user.id)
    free_space = factory["storage_capacity"] - storage_used
    if amount > free_space:
        await callback.answer("❌ انبارت جا نداره، اول بفروش یا ارتقا بده.", show_alert=True)
        return

    add_meow_points(callback.from_user.id, -total_cost)
    start_factory_production(callback.from_user.id, product_key, amount, int(time.time()))

    await callback.answer(f"✅ تولید {amount} عدد «{product['name']}» شروع شد!", show_alert=True)
    await _refresh_factory_panel(callback, callback.from_user.id)


@router.callback_query(F.data == "factory_collect")
async def cb_factory_collect(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return
    factory = get_factory(callback.from_user.id)
    if not factory or not factory["current_product"]:
        await callback.answer("❌ چیزی برای برداشت نیست.", show_alert=True)
        return
    if not _is_production_ready(factory):
        await callback.answer("⏳ تولید هنوز آماده نیست.", show_alert=True)
        return

    product_key = factory["current_product"]
    product = FACTORY_PRODUCTS.get(product_key, {"name": product_key, "xp_per_unit": 0})
    produced = factory["production_amount"]
    xp_gained = produced * product["xp_per_unit"]

    collect_factory_production(callback.from_user.id, product_key, produced, xp_gained)

    # چک ارتقای سطح کارخونه بعد از اضافه شدن XP
    factory = get_factory(callback.from_user.id)
    xp_needed = _xp_needed_for_level(factory["level"])
    if factory["xp"] >= xp_needed and factory["level"] < FACTORY_MAX_FACTORY_LEVEL:
        set_factory_level(callback.from_user.id, factory["level"] + 1, factory["xp"] - xp_needed)

    await callback.answer(f"📦 {produced} عدد «{product['name']}» به انبار اضافه شد!", show_alert=True)
    await _refresh_factory_panel(callback, callback.from_user.id)


# ---------------- انبار ----------------

def _factory_storage_text(factory):
    items = get_factory_storage_items(factory["user_id"])
    lines = [
        "🏭 کارخونه جوجویی",
        "",
        "محصولات انبار ✨",
    ]
    if not items:
        lines.append("❗️ هیچ محصولی در انبار موجود نیست.")
    else:
        for item in items:
            product = FACTORY_PRODUCTS.get(item["product_key"])
            name = product["name"] if product else item["product_key"]
            emoji = product["emoji"] if product else ""
            lines.append(f"{emoji} {name}: {item['amount']:,}")

    if factory["storage_level"] < 30:
        next_capacity = factory["storage_capacity"] + FACTORY_STORAGE_GROWTH_PER_LEVEL
        cost = _storage_upgrade_cost(factory["storage_level"])
        lines.append("")
        lines.append("سطح بعدی انبار کارخونه ⭐")
        lines.append(f"ظرفیت جدید : {next_capacity:,} محصول ✨")
        lines.append(f"هزینه ارتقا انبار : {cost:,} 💰")

    text = "\n".join(lines)
    return build_premium_entities(text, [("🏭", "factory"), ("✨", "sparkle"), ("⭐", "star"), ("💰", "money_bag")])


@router.callback_query(F.data == "factory_storage")
async def cb_factory_storage(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return
    factory = get_factory(callback.from_user.id)
    if not factory:
        await callback.answer("❌ اول باید کارخونه بسازی.", show_alert=True)
        return

    items = get_factory_storage_items(callback.from_user.id)
    text, entities = _factory_storage_text(factory)
    await callback.message.edit_text(
        text, entities=entities or None,
        reply_markup=factory_storage_kb(has_items=bool(items)),
    )
    await callback.answer()


@router.callback_query(F.data == "factory_sell_all")
async def cb_factory_sell_all(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return
    items = get_factory_storage_items(callback.from_user.id)
    if not items:
        await callback.answer("❌ انبارت خالیه.", show_alert=True)
        return

    total_revenue = 0
    for item in items:
        product = FACTORY_PRODUCTS.get(item["product_key"])
        if not product:
            continue
        total_revenue += item["amount"] * product["sell_price"]

    sell_all_factory_storage(callback.from_user.id)
    add_meow_points(callback.from_user.id, total_revenue)

    await callback.answer(f"💰 کل انبار فروخته شد؛ {total_revenue:,} {CURRENCY_EMOJI} گرفتی!", show_alert=True)
    factory = get_factory(callback.from_user.id)
    items = get_factory_storage_items(callback.from_user.id)
    text, entities = _factory_storage_text(factory)
    await callback.message.edit_text(
        text, entities=entities or None,
        reply_markup=factory_storage_kb(has_items=bool(items)),
    )


@router.callback_query(F.data == "factory_upgrade_storage")
async def cb_factory_upgrade_storage(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return
    user = get_user(callback.from_user.id)
    factory = get_factory(callback.from_user.id)
    if not factory:
        await callback.answer("❌ اول باید کارخونه بسازی.", show_alert=True)
        return
    if factory["storage_level"] >= 30:
        await callback.answer("🏆 انبار به بالاترین سطح رسیده.", show_alert=True)
        return

    cost = _storage_upgrade_cost(factory["storage_level"])
    if user["meow_points"] < cost:
        await callback.answer(f"❌ برای ارتقا {cost:,} {CURRENCY_EMOJI} نیاز داری.", show_alert=True)
        return

    new_level = factory["storage_level"] + 1
    new_capacity = factory["storage_capacity"] + FACTORY_STORAGE_GROWTH_PER_LEVEL

    add_meow_points(callback.from_user.id, -cost)
    upgrade_factory_storage(callback.from_user.id, new_level, new_capacity)

    await callback.answer(f"⭐ انبار به سطح {new_level} ارتقا یافت!", show_alert=True)
    factory = get_factory(callback.from_user.id)
    items = get_factory_storage_items(callback.from_user.id)
    text, entities = _factory_storage_text(factory)
    await callback.message.edit_text(
        text, entities=entities or None,
        reply_markup=factory_storage_kb(has_items=bool(items)),
    )


# ---------------- کارگران ----------------

def _factory_workers_text(factory):
    lines = [
        "🏭 کارخونه جوجویی",
        "",
        "کارگران کارخونه 🐱",
        f"تعداد کارگران کارخونه : {factory['workers_count']} پیشی 🐱",
        f"تعداد صندلی‌های کارخونه : {factory['seats_count']} صندلی 🪑",
        f"سطح : {factory['seats_level']} ⭐",
    ]

    if factory["seats_level"] < 30:
        next_seats = factory["seats_count"] + FACTORY_SEATS_GROWTH_PER_LEVEL
        cost = _seats_upgrade_cost(factory["seats_level"])
        lines.append("")
        lines.append("سطح بعدی صندلی کارکنان کارخونه ⭐")
        lines.append(f"تعداد صندلی‌های جدید : {next_seats} صندلی 🪑")
        lines.append(f"هزینه ارتقا صندلی کارکنان : {cost:,} 💰")

    lines.append("")
    lines.append(f"هزینه استخدام هر کارگر : {FACTORY_WORKER_HIRE_COST:,} 💰")

    text = "\n".join(lines)
    return build_premium_entities(text, [("🏭", "factory"), ("🐱", "worker"), ("🪑", "seat"), ("⭐", "star"), ("💰", "money_bag")])


@router.callback_query(F.data == "factory_workers")
async def cb_factory_workers_menu(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return
    factory = get_factory(callback.from_user.id)
    if not factory:
        await callback.answer("❌ اول باید کارخونه بسازی.", show_alert=True)
        return

    text, entities = _factory_workers_text(factory)
    await callback.message.edit_text(
        text, entities=entities or None,
        reply_markup=factory_workers_kb(
            can_hire=factory["workers_count"] < factory["seats_count"],
            can_fire=factory["workers_count"] > 0,
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "factory_hire")
async def cb_factory_hire(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return
    user = get_user(callback.from_user.id)
    factory = get_factory(callback.from_user.id)
    if not factory:
        await callback.answer("❌ اول باید کارخونه بسازی.", show_alert=True)
        return
    if factory["workers_count"] >= factory["seats_count"]:
        await callback.answer("❌ صندلی خالی نداری، اول ارتقا بده.", show_alert=True)
        return
    if user["meow_points"] < FACTORY_WORKER_HIRE_COST:
        await callback.answer(f"❌ برای استخدام {FACTORY_WORKER_HIRE_COST:,} {CURRENCY_EMOJI} نیاز داری.", show_alert=True)
        return

    add_meow_points(callback.from_user.id, -FACTORY_WORKER_HIRE_COST)
    hire_factory_worker(callback.from_user.id)

    await callback.answer("✅ یه کارگر جدید استخدام شد!", show_alert=True)
    factory = get_factory(callback.from_user.id)
    text, entities = _factory_workers_text(factory)
    await callback.message.edit_text(
        text, entities=entities or None,
        reply_markup=factory_workers_kb(
            can_hire=factory["workers_count"] < factory["seats_count"],
            can_fire=factory["workers_count"] > 0,
        ),
    )


@router.callback_query(F.data == "factory_fire")
async def cb_factory_fire(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return
    factory = get_factory(callback.from_user.id)
    if not factory or factory["workers_count"] <= 0:
        await callback.answer("❌ کارگری برای اخراج نداری.", show_alert=True)
        return

    refund = int(FACTORY_WORKER_HIRE_COST * FACTORY_WORKER_FIRE_REFUND_RATIO)
    fire_factory_worker(callback.from_user.id)
    add_meow_points(callback.from_user.id, refund)

    await callback.answer(f"🚫 یه کارگر اخراج شد. {refund:,} {CURRENCY_EMOJI} برگشت داده شد.", show_alert=True)
    factory = get_factory(callback.from_user.id)
    text, entities = _factory_workers_text(factory)
    await callback.message.edit_text(
        text, entities=entities or None,
        reply_markup=factory_workers_kb(
            can_hire=factory["workers_count"] < factory["seats_count"],
            can_fire=factory["workers_count"] > 0,
        ),
    )


@router.callback_query(F.data == "factory_upgrade_seats")
async def cb_factory_upgrade_seats(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return
    user = get_user(callback.from_user.id)
    factory = get_factory(callback.from_user.id)
    if not factory:
        await callback.answer("❌ اول باید کارخونه بسازی.", show_alert=True)
        return
    if factory["seats_level"] >= 30:
        await callback.answer("🏆 صندلی‌ها به بالاترین سطح رسیده.", show_alert=True)
        return

    cost = _seats_upgrade_cost(factory["seats_level"])
    if user["meow_points"] < cost:
        await callback.answer(f"❌ برای ارتقا {cost:,} {CURRENCY_EMOJI} نیاز داری.", show_alert=True)
        return

    new_level = factory["seats_level"] + 1
    new_seats = factory["seats_count"] + FACTORY_SEATS_GROWTH_PER_LEVEL

    add_meow_points(callback.from_user.id, -cost)
    upgrade_factory_seats(callback.from_user.id, new_level, new_seats)

    await callback.answer(f"⭐ صندلی‌ها به سطح {new_level} ارتقا یافت!", show_alert=True)
    factory = get_factory(callback.from_user.id)
    text, entities = _factory_workers_text(factory)
    await callback.message.edit_text(
        text, entities=entities or None,
        reply_markup=factory_workers_kb(
            can_hire=factory["workers_count"] < factory["seats_count"],
            can_fire=factory["workers_count"] > 0,
        ),
    )


# ---------------- دستگاه‌های تولید ----------------

def _factory_devices_text(factory):
    lines = [
        "🏭 کارخونه جوجویی",
        "",
        "دستگاه‌های تولید 🖨",
        f"زمان مورد نیاز برای تولید : {factory['production_speed_seconds']} ثانیه ⏳",
        f"سطح : {factory['device_level']} ⭐",
    ]

    if factory["device_level"] < 30 and factory["production_speed_seconds"] > FACTORY_DEVICE_MIN_SPEED_SECONDS:
        next_speed = _next_device_speed(factory["production_speed_seconds"])
        cost = _device_upgrade_cost(factory["device_level"])
        lines.append("")
        lines.append("سطح بعدی دستگاه‌های تولید کارخونه ✨")
        lines.append(f"زمان مورد نیاز برای تولید : {next_speed} ثانیه ⏳")
        lines.append("")
        lines.append(f"هزینه ارتقا دستگاه‌های تولید : {cost:,} 💰")
    else:
        lines.append("\n🏆 دستگاه‌ها به بالاترین سرعت ممکن رسیدن.")

    text = "\n".join(lines)
    return build_premium_entities(text, [("⭐", "star"), ("⏳", "clock"), ("✨", "sparkle"), ("💰", "money_bag")])


@router.callback_query(F.data == "factory_devices")
async def cb_factory_devices_menu(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return
    factory = get_factory(callback.from_user.id)
    if not factory:
        await callback.answer("❌ اول باید کارخونه بسازی.", show_alert=True)
        return

    text, entities = _factory_devices_text(factory)
    await callback.message.edit_text(text, entities=entities or None, reply_markup=factory_devices_kb())
    await callback.answer()


@router.callback_query(F.data == "factory_upgrade_device")
async def cb_factory_upgrade_device(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return
    user = get_user(callback.from_user.id)
    factory = get_factory(callback.from_user.id)
    if not factory:
        await callback.answer("❌ اول باید کارخونه بسازی.", show_alert=True)
        return
    if factory["production_speed_seconds"] <= FACTORY_DEVICE_MIN_SPEED_SECONDS:
        await callback.answer("🏆 دستگاه‌ها به بالاترین سرعت رسیدن.", show_alert=True)
        return

    cost = _device_upgrade_cost(factory["device_level"])
    if user["meow_points"] < cost:
        await callback.answer(f"❌ برای ارتقا {cost:,} {CURRENCY_EMOJI} نیاز داری.", show_alert=True)
        return

    new_level = factory["device_level"] + 1
    new_speed = _next_device_speed(factory["production_speed_seconds"])

    add_meow_points(callback.from_user.id, -cost)
    upgrade_factory_device(callback.from_user.id, new_level, new_speed)

    await callback.answer(f"⭐ دستگاه‌ها به سطح {new_level} ارتقا یافت!", show_alert=True)
    factory = get_factory(callback.from_user.id)
    text, entities = _factory_devices_text(factory)
    await callback.message.edit_text(text, entities=entities or None, reply_markup=factory_devices_kb())

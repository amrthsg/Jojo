# handlers/jojoyi.py
# پروفایل پیشرفته «جوجویی» - شکم/سیری، تولید خودکار پوینت، مقام ویژه
# با نوشتن «جوجویی» باز میشه؛ با نوشتن «گرفتن کرم» شکم سیر میشه.

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database.models import (
    get_user,
    add_meow_points,
    get_jojoyi_stats,
    create_jojoyi_stats_if_not_exists,
    apply_jojoyi_production,
    feed_jojoyi,
    collect_jojoyi_points,
    upgrade_jojoyi_rank,
    set_panel_owner,
    is_panel_owner,
)
from keyboards.main_kb import jojoyi_menu_kb
from utils.premium_emoji import build_premium_entities
from config import (
    JOJOYI_BASE_BELLY_MAX,
    JOJOYI_BELLY_DROP_INTERVAL_SECONDS,
    JOJOYI_FEED_COST,
    JOJOYI_FEED_BELLY_RESTORE,
    JOJOYI_BASE_PRODUCTION_RATE,
    JOJOYI_BASE_PRODUCTION_CAPACITY,
    JOJOYI_RANKS,
    JOJOYI_MAX_RANK,
    CURRENCY_EMOJI,
)

router = Router()


async def _guard_owner(callback: CallbackQuery) -> bool:
    owner_ok = is_panel_owner(callback.message.chat.id, callback.message.message_id, callback.from_user.id)
    if not owner_ok:
        await callback.answer("⛔️ این پنل برای شما نیست جوجو 🐤", show_alert=True)
        return False
    return True


def _ensure_stats(user_id: int):
    """اگه کاربر پروفایل جوجویی نداشت، با مقادیر پایه میسازدش"""
    create_jojoyi_stats_if_not_exists(
        user_id,
        JOJOYI_BASE_BELLY_MAX,
        JOJOYI_BASE_PRODUCTION_RATE,
        JOJOYI_BASE_PRODUCTION_CAPACITY,
    )


def _jojoyi_text(user, stats):
    rank_info = JOJOYI_RANKS.get(stats["jojoyi_rank"], JOJOYI_RANKS[1])
    rank_name = rank_info["name"]

    lines = [
        "🐤 پروفایل جوجویی",
        "━━━━━━━━━━━━━",
        "",
        f"❤️ نام : {user['pet_name']}",
    ]

    if stats["belly"] <= 0:
        lines.append("😿 شکم : دیگه کار نمیکنم، گرسنمه!")
    else:
        lines.append(f"🍖 شکم : ({stats['belly']} / {stats['belly_max']})")

    lines.append("")
    lines.append(f"🏅 مقام : {rank_name}")
    lines.append(f"⭐ سطح : {stats['jojoyi_rank']} / {JOJOYI_MAX_RANK}")
    lines.append("")
    lines.append(f"🪙 پوینت‌های تولید شده : {stats['produced_total']:,}")
    lines.append(f"⚡️ تولید پوینت در ثانیه : {stats['production_rate']:g}")
    lines.append(f"📦 ظرفیت : {stats['pending_points']:,} / {stats['production_capacity']:,}")

    if stats["jojoyi_rank"] < JOJOYI_MAX_RANK:
        next_rank_info = JOJOYI_RANKS[stats["jojoyi_rank"] + 1]
        lines.append("")
        lines.append(f"💰 هزینه ارتقا مقام : {next_rank_info['upgrade_cost']:,}")

    text = "\n".join(lines)
    placeholders = [
        ("❤️", "fire2"), ("🏅", "trophy"), ("⭐", "star"), ("🪙", "coin"),
        ("⚡️", "xp"), ("📦", "storage"), ("💰", "money_bag"),
    ]
    return build_premium_entities(text, placeholders)


async def _send_jojoyi_panel(message_or_callback, user_id: int, edit: bool = False):
    user = get_user(user_id)
    if not user:
        text = "اول باید /start بزنی 🐤"
        target = message_or_callback.message if edit else message_or_callback
        await (target.edit_text(text) if edit else target.answer(text))
        return

    _ensure_stats(user_id)
    apply_jojoyi_production(user_id, JOJOYI_BELLY_DROP_INTERVAL_SECONDS)
    stats = get_jojoyi_stats(user_id)

    text, entities = _jojoyi_text(user, stats)
    has_pending = stats["pending_points"] > 0
    can_upgrade = stats["jojoyi_rank"] < JOJOYI_MAX_RANK
    kb = jojoyi_menu_kb(has_pending, can_upgrade)

    if edit:
        await message_or_callback.message.edit_text(text, entities=entities or None, reply_markup=kb)
        set_panel_owner(message_or_callback.message.chat.id, message_or_callback.message.message_id, user_id)
    else:
        sent = await message_or_callback.answer(text, entities=entities or None, reply_markup=kb)
        set_panel_owner(sent.chat.id, sent.message_id, user_id)


@router.message(F.text == "جوجویی")
async def handle_jojoyi_menu(message: Message):
    await _send_jojoyi_panel(message, message.from_user.id)


@router.callback_query(F.data == "jojoyi_collect")
async def cb_jojoyi_collect(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return

    amount = collect_jojoyi_points(callback.from_user.id)
    if amount <= 0:
        await callback.answer("❌ چیزی برای برداشت نیست.", show_alert=True)
        return

    add_meow_points(callback.from_user.id, amount)
    await callback.answer(f"🪙 {amount:,} {CURRENCY_EMOJI} به موجودیت اضافه شد!", show_alert=True)
    await _send_jojoyi_panel(callback, callback.from_user.id, edit=True)


@router.callback_query(F.data == "jojoyi_upgrade")
async def cb_jojoyi_upgrade(callback: CallbackQuery):
    if not await _guard_owner(callback):
        return

    user = get_user(callback.from_user.id)
    _ensure_stats(callback.from_user.id)
    stats = get_jojoyi_stats(callback.from_user.id)

    if stats["jojoyi_rank"] >= JOJOYI_MAX_RANK:
        await callback.answer("🏆 به بالاترین مقام رسیدی!", show_alert=True)
        return

    next_rank = stats["jojoyi_rank"] + 1
    next_rank_info = JOJOYI_RANKS[next_rank]
    cost = next_rank_info["upgrade_cost"]

    if user["meow_points"] < cost:
        await callback.answer(f"❌ برای ارتقا به «{next_rank_info['name']}» {cost:,} {CURRENCY_EMOJI} نیاز داری.", show_alert=True)
        return

    add_meow_points(callback.from_user.id, -cost)
    upgrade_jojoyi_rank(
        callback.from_user.id,
        next_rank,
        next_rank_info["belly_max"],
        next_rank_info["production_rate"],
        next_rank_info["capacity"],
    )

    await callback.answer(f"🎉 مقامت به «{next_rank_info['name']}» ارتقا یافت!", show_alert=True)
    await _send_jojoyi_panel(callback, callback.from_user.id, edit=True)


@router.message(F.text == "گرفتن کرم")
async def handle_feed_jojoyi(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer("اول باید /start بزنی 🐤")
        return

    _ensure_stats(user_id)
    apply_jojoyi_production(user_id, JOJOYI_BELLY_DROP_INTERVAL_SECONDS)
    stats = get_jojoyi_stats(user_id)

    if stats["belly"] >= stats["belly_max"]:
        text = "😋 شکمت الان کاملاً سیره، نیازی به کرم نداری."
        text, entities = build_premium_entities(text, [])
        await message.answer(text, entities=entities or None)
        return

    if user["meow_points"] < JOJOYI_FEED_COST:
        text = f"❌ برای گرفتن کرم به {JOJOYI_FEED_COST:,} {CURRENCY_EMOJI} نیاز داری."
        text, entities = build_premium_entities(text, [])
        await message.answer(text, entities=entities or None)
        return

    add_meow_points(user_id, -JOJOYI_FEED_COST)
    feed_jojoyi(user_id, JOJOYI_FEED_BELLY_RESTORE)

    stats = get_jojoyi_stats(user_id)
    text = f"🐛 کرم گرفتی! شکمت پر شد. ({stats['belly']} / {stats['belly_max']})"
    text, entities = build_premium_entities(text, [])
    await message.answer(text, entities=entities or None)

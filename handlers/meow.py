# handlers/meow.py
# هندلر اصلی: جوجو جوجو کن، تجربه و سطح، پروفایل

import time
from aiogram import Router, F
from aiogram.types import Message

from database.models import (
    get_user,
    add_meow_points,
    add_exp,
    set_last_meow_time,
    set_level,
)
from utils.leveling import (
    get_cooldown_seconds,
    perform_meow,
    check_level_up,
    get_exp_required_for_level,
    get_level_up_reward,
    get_capacity_for_rank,
    format_time,
)
from config import CURRENCY_NAME, CURRENCY_EMOJI, MAX_LEVEL

router = Router()


async def process_meow(message: Message):
    """
    منطق اصلی میو کردن. هم از دکمه «🐣 جوجو جوجو کن» و هم از تایپ
    مستقیم نام جوجو (مثلاً «جوجو») صدا زده میشه.
    """
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user:
        await message.answer("اول باید /start بزنی تا جوجوت ساخته بشه 🐤")
        return

    if user["is_banned"]:
        await message.answer("🚫 حساب شما مسدود شده است.")
        return

    now = int(time.time())
    cooldown = get_cooldown_seconds(user["level"])
    elapsed = now - user["last_meow_time"]

    if elapsed < cooldown:
        remaining = cooldown - elapsed
        await message.answer(
            f"😴 {user['pet_name']} هنوز خسته‌ست..\n"
            f"⏳ بعد از {format_time(remaining)} میتونی دوباره {user['pet_name']} کنی"
        )
        return

    # محاسبه پاداش
    reward = perform_meow(user["level"])

    # چک ظرفیت (شکم/جیب)
    new_balance = user["meow_points"] + reward
    if new_balance > user["capacity"]:
        reward = max(0, user["capacity"] - user["meow_points"])
        new_balance = user["capacity"]

    add_meow_points(user_id, reward)
    add_exp(user_id, 1)
    set_last_meow_time(user_id, now)

    # چک ارتقای سطح
    new_exp = user["exp"] + 1
    new_level, leveled_up = check_level_up(user["level"], new_exp)

    level_up_text = ""
    if leveled_up:
        # هر ۵ سطح، رنک بالا میره (ریست exp/level داخل رنک - اختیاریه، اینجا ساده نگه داشتیم)
        new_rank = (new_level - 1) // 5 + 1
        new_capacity = get_capacity_for_rank(new_rank)
        bonus = get_level_up_reward(new_level)

        add_meow_points(user_id, bonus)
        set_level(user_id, new_level, new_capacity, new_rank)

        level_up_text = (
            f"\n\n🎉 <b>{user['pet_name']} به سطح {new_level} رسید!</b>\n"
            f"🎁 جایزه ارتقا: {bonus:,} {CURRENCY_EMOJI}"
        )

    new_cooldown = get_cooldown_seconds(new_level)

    text = (
        f"<b>{user['pet_name']}</b> {reward:,} {CURRENCY_NAME} گرفتی 🐣\n"
        f"💰 {CURRENCY_NAME} هات : {new_balance:,} {CURRENCY_EMOJI}\n"
        f"⏳ بعد از {format_time(new_cooldown)} میتونی دوباره {user['pet_name']} کنی"
        f"{level_up_text}"
    )

    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🐣 جوجو جوجو کن")
async def handle_meow_button(message: Message):
    await process_meow(message)


def _is_pet_name_call(text: str | None) -> bool:
    """
    چک می‌کنه آیا متن پیام میتونه صدا زدنِ نام جوجو باشه.
    برای جلوگیری از تداخل با دکمه‌های منو (که همه با ایموجی شروع میشن)
    و دستورات (که با / شروع میشن) فیلتر میشه.
    """
    if not text:
        return False
    text = text.strip()
    if text.startswith("/"):
        return False
    if len(text) < 1 or len(text) > 32:
        return False
    if any(text.startswith(prefix) for prefix in ("🐣", "🪙", "⭐", "🎮", "🏦", "🛍", "🏆", "🪪")):
        return False
    return True


@router.message(F.chat.type == "private", F.text.func(_is_pet_name_call))
async def handle_meow_by_pet_name(message: Message):
    """
    وقتی کاربر مستقیم اسم جوجوش رو تایپ می‌کنه (مثلاً «جوجو»)،
    اگه دقیقاً با نام جوجوی ثبت‌شده‌ی خودش یکی باشه، همون کار دکمه میو رو انجام میده.

    عمداً فقط تو چت خصوصی (private) فعاله؛ در گروه‌ها محدود میشه چون ممکنه
    پیام‌های عادی کاربران دیگه به‌اشتباه به‌عنوان صدا زدن جوجو تفسیر بشه.
    """
    user = get_user(message.from_user.id)
    if not user:
        return  # کاربر هنوز /start نزده، این پیام رو نادیده بگیر

    if message.text.strip() != user["pet_name"]:
        return  # این پیام اسم جوجو این کاربر نیست، نادیده بگیر

    await process_meow(message)


@router.message(F.text == "⭐ تجربه و سطح")
async def handle_level_info(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user:
        await message.answer("اول باید /start بزنی 🐤")
        return

    if user["level"] >= MAX_LEVEL:
        exp_text = "به حداکثر سطح رسیدی! 🏆"
    else:
        needed = get_exp_required_for_level(user["level"] + 1)
        remaining = max(0, needed - user["exp"])
        exp_text = f"تا سطح بعدی: {remaining} میو مونده"

    text = (
        f"⭐ <b>سطح و تجربه {user['pet_name']}</b>\n\n"
        f"🌟 سطح فعلی: {user['level']} / {MAX_LEVEL}\n"
        f"🐣 مجموع میو: {user['exp']:,}\n"
        f"👑 مقام: {user['rank_level']}\n\n"
        f"{exp_text}"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🪙 جوجو پوینت")
async def handle_points_info(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user:
        await message.answer("اول باید /start بزنی 🐤")
        return

    text = (
        f"💰 <b>{CURRENCY_NAME} های {user['pet_name']}</b>\n\n"
        f"🪙 موجودی: {user['meow_points']:,} {CURRENCY_EMOJI}\n"
        f"🎒 ظرفیت: {user['capacity']:,} {CURRENCY_EMOJI}\n"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🪪 پروفایل جوجو")
async def handle_profile(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user:
        await message.answer("اول باید /start بزنی 🐤")
        return

    fill_percent = int((user["meow_points"] / user["capacity"]) * 100) if user["capacity"] else 0

    text = (
        f"🐣 <b>پروفایل {user['pet_name']}</b>\n\n"
        f"🏷 نام: {user['pet_name']}\n"
        f"👑 مقام: {user['rank_level']}\n"
        f"⭐ سطح: {user['level']} / {MAX_LEVEL}\n\n"
        f"🪙 موجودی: {user['meow_points']:,} {CURRENCY_EMOJI}\n"
        f"🎒 ظرفیت پر شده: {fill_percent}%\n"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text.startswith("تغییر نام "))
async def handle_rename(message: Message):
    """
    فرمت: تغییر نام {اسم جدید}
    """
    from database.models import update_pet_name
    from config import CARD_NUMBER_CHANGE_COST  # فقط برای الگو، هزینه واقعی زیر تعریف شده

    RENAME_COST = 75
    new_name = message.text.replace("تغییر نام ", "").strip()

    if not (3 <= len(new_name) <= 32):
        await message.answer("❌ نام جوجو باید بین ۳ تا ۳۲ کاراکتر باشد.")
        return

    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        await message.answer("اول باید /start بزنی 🐤")
        return

    if user["meow_points"] < RENAME_COST:
        await message.answer(f"❌ برای تغییر نام به {RENAME_COST} {CURRENCY_EMOJI} نیاز داری.")
        return

    add_meow_points(user_id, -RENAME_COST)
    update_pet_name(user_id, new_name)

    await message.answer(f"✅ نام جوجوت به «{new_name}» تغییر کرد 🐣")

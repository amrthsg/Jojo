# handlers/meow.py
# هندلر اصلی: جیک کردن (با تایپ کلمه «جیک جیک»)، تجربه و سطح، پروفایل
# هیچ دکمه‌ای اینجا نیست، همه‌چیز با تایپ متن فراخوانی میشه.

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
from config import CURRENCY_NAME, CURRENCY_EMOJI, MAX_LEVEL, TRANSFER_MIN_AMOUNT, TRANSFER_MAX_AMOUNT, TRANSFER_MIN_LEVEL
from utils.amount_parser import parse_amount

router = Router()

JIK_TRIGGER = "جیک جیک"


async def process_meow(message: Message):
    """
    منطق اصلی جیک کردن. فقط با تایپ دقیق کلمه «جیک جیک» صدا زده میشه.
    """
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user:
        await message.answer("اول باید /start بزنی تا جوجوت ساخته بشه 🐤")
        return

    if user["is_banned"]:
        await message.answer("🚫 حساب شما مسدود شده است.")
        return

    if user["is_jailed"]:
        await message.answer("🔒 جوجوت الان زندانیه! باید منتظر آزادی از طرف ادمین بمونی.")
        return

    now = int(time.time())
    cooldown = get_cooldown_seconds(user["level"])
    elapsed = now - user["last_meow_time"]

    if elapsed < cooldown:
        remaining = cooldown - elapsed
        await message.answer(
            f"😴 {user['pet_name']} هنوز خسته‌ست..\n"
            f"⏳ بعد از {format_time(remaining)} میتونی دوباره جیک جیک کنی"
        )
        return

    # محاسبه پاداش (بدون محدودیت سقف ظرفیت)
    reward = perform_meow(user["level"])
    new_balance = user["meow_points"] + reward

    add_meow_points(user_id, reward)
    add_exp(user_id, 1)
    set_last_meow_time(user_id, now)

    # چک ارتقای سطح
    new_exp = user["exp"] + 1
    new_level, leveled_up = check_level_up(user["level"], new_exp)

    level_up_text = ""
    if leveled_up:
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
        f"<b>{user['pet_name']}</b> {reward:,} {CURRENCY_NAME} گرفتی 🐤\n"
        f"💰 {CURRENCY_NAME} هات : {new_balance:,} {CURRENCY_EMOJI}\n"
        f"⏳ بعد از {format_time(new_cooldown)} میتونی دوباره جیک جیک کنی"
        f"{level_up_text}"
    )

    await message.answer(text, parse_mode="HTML")


@router.message(F.text == JIK_TRIGGER)
async def handle_jik_jik(message: Message):
    """
    محرک اصلی: کاربر باید دقیقاً کلمه «جیک جیک» رو تایپ کنه تا پوینت بگیره.
    هم تو چت خصوصی هم تو گروه فعاله.
    """
    await process_meow(message)


@router.message(F.text.in_({"سطح", "تجربه", "تجربه و سطح"}))
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
        exp_text = f"تا سطح بعدی: {remaining} جیک مونده"

    text = (
        f"⭐ <b>سطح و تجربه {user['pet_name']}</b>\n\n"
        f"🌟 سطح فعلی: {user['level']} / {MAX_LEVEL}\n"
        f"🐤 مجموع جیک: {user['exp']:,}\n"
        f"👑 مقام: {user['rank_level']}\n\n"
        f"{exp_text}"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text.in_({"پوینت", "جیک پوینت", "موجودی"}))
async def handle_points_info(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user:
        await message.answer("اول باید /start بزنی 🐤")
        return

    text = (
        f"💰 <b>{CURRENCY_NAME} های {user['pet_name']}</b>\n\n"
        f"🪙 موجودی: {user['meow_points']:,} {CURRENCY_EMOJI}\n"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text.in_({"پروفایل", "پروفایل جوجو"}))
async def handle_profile(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user:
        await message.answer("اول باید /start بزنی 🐤")
        return

    tg_user = message.from_user
    full_name = tg_user.full_name  # ترکیب first_name و last_name تلگرام
    username_line = f"🔗 @{tg_user.username}\n" if tg_user.username else ""

    text = (
        f"👤 <b>{full_name}</b>\n"
        f"{username_line}\n"
        f"🐤 <b>پروفایل {user['pet_name']}</b>\n\n"
        f"🏷 نام جوجو: {user['pet_name']}\n"
        f"👑 مقام: {user['rank_level']}\n"
        f"⭐ سطح: {user['level']} / {MAX_LEVEL}\n\n"
        f"🪙 موجودی: {user['meow_points']:,} {CURRENCY_EMOJI}\n"
    )

    # تلاش برای گرفتن عکس پروفایل واقعی تلگرام کاربر و فرستادن به همراه متن
    try:
        photos = await message.bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            photo_file_id = photos.photos[0][-1].file_id  # بزرگترین سایز عکس
            await message.answer_photo(photo_file_id, caption=text, parse_mode="HTML")
            return
    except Exception:
        pass  # اگه عکس نداشت یا خطا داد، فقط متن رو میفرستیم

    await message.answer(text, parse_mode="HTML")


@router.message(F.text.startswith("تغییر نام "))
async def handle_rename(message: Message):
    """
    فرمت: تغییر نام {اسم جدید}
    """
    from database.models import update_pet_name

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

    await message.answer(f"✅ نام جوجوت به «{new_name}» تغییر کرد 🐤")


@router.message(F.text.startswith("انتقال جیک "))
async def handle_transfer_jik(message: Message):
    """
    فرمت: باید روی پیام کاربر مقصد ریپلای کنی و بنویسی «انتقال جیک {مقدار}»
    مقدار میتونه با پسوند k/m/کک هم باشه، مثلاً: انتقال جیک 5k
    """
    if not message.reply_to_message:
        await message.answer("❌ باید روی پیام کاربر مقصد ریپلای کنی و بنویسی «انتقال جیک {مبلغ}»")
        return

    to_user_id = message.reply_to_message.from_user.id
    from_user_id = message.from_user.id

    if to_user_id == from_user_id:
        await message.answer("❌ نمیتونی به خودت انتقال بدی.")
        return

    amount_str = message.text.replace("انتقال جیک ", "", 1).strip()
    amount = parse_amount(amount_str)

    if amount is None or amount <= 0:
        await message.answer("❌ مبلغ نامعتبره. مثال درست: انتقال جیک 500 یا انتقال جیک 5k")
        return

    if amount < TRANSFER_MIN_AMOUNT:
        await message.answer(f"❌ حداقل مبلغ انتقال {TRANSFER_MIN_AMOUNT:,} {CURRENCY_EMOJI} است.")
        return

    if amount > TRANSFER_MAX_AMOUNT:
        await message.answer(f"❌ حداکثر مبلغ انتقال {TRANSFER_MAX_AMOUNT:,} {CURRENCY_EMOJI} است.")
        return

    from_user = get_user(from_user_id)
    if not from_user:
        await message.answer("اول باید /start بزنی 🐤")
        return

    if from_user["level"] < TRANSFER_MIN_LEVEL:
        await message.answer(f"❌ برای انتقال جیک پوینت باید حداقل سطح {TRANSFER_MIN_LEVEL} باشی.")
        return

    if not get_user(to_user_id):
        await message.answer("❌ کاربر مقصد هنوز /start نزده.")
        return

    if from_user["meow_points"] < amount:
        await message.answer("❌ موجودی کافی نداری.")
        return

    add_meow_points(from_user_id, -amount)
    add_meow_points(to_user_id, amount)

    await message.answer(
        f"✅ {amount:,} {CURRENCY_EMOJI} به {message.reply_to_message.from_user.full_name} انتقال یافت."
    )

    try:
        await message.bot.send_message(
            to_user_id,
            f"💰 {amount:,} {CURRENCY_EMOJI} از طرف {message.from_user.full_name} برات ارسال شد!",
        )
    except Exception:
        pass

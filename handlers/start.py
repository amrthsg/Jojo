# handlers/start.py
# هندلر /start - ساخت کاربر جدید و خوش‌آمدگویی

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart

from database.models import create_user_if_not_exists, get_user
from keyboards.main_kb import main_menu_kb
from config import DEFAULT_PET_NAME, CURRENCY_NAME

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    is_new = create_user_if_not_exists(user_id, username)

    if is_new:
        text = (
            f"🐾 <b>ربات سرگرمی جوجو</b>\n\n"
            f"🐱 یه {DEFAULT_PET_NAME} بامزه برات ساخته شد!\n\n"
            f"کافیه دکمه «🐾 میو میو کن» رو بزنی تا {CURRENCY_NAME} جمع کنی و سطح بگیری.\n\n"
            f"✨ چرا جوجو؟\n"
            f"⚡ پاسخگویی فوق‌العاده سریع\n"
            f"🎮 بازی‌های سرگرم‌کننده\n"
            f"🏦 بانک و مارکت اختصاصی\n"
            f"🎉 کاملاً رایگان برای همه\n"
        )
    else:
        user = get_user(user_id)
        text = f"سلام دوباره {user['pet_name']} 🐾 خوش برگشتی!"

    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")

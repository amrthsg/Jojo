# handlers/start.py
# هندلر /start - ساخت کاربر جدید، پیام معرفی و راهنما

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from database.models import create_user_if_not_exists, get_user
from keyboards.main_kb import main_menu_kb, welcome_inline_kb
from config import DEFAULT_PET_NAME, CURRENCY_NAME

router = Router()


def _welcome_text() -> str:
    return (
        f"🐣 <b>ربات سرگرمی جوجو</b> 🐣\n\n"
        f"یه {DEFAULT_PET_NAME} بامزه برای گروهت...\n"
        f"🌸 کافیه توی گروه جوجو جوجو کنی تا {CURRENCY_NAME} بگیری!\n\n"
        f"⭐ {CURRENCY_NAME} جمع کن و با بقیه رقابت کن\n"
        f"🐣👑 لیدربرد جوجویی رو فتح کن و سلطان جوجوها شو\n\n"
        f"⭐ چرا جوجو؟\n"
        f"⚡ پاسخگویی فوق‌العاده سریع\n"
        f"🛠 عملکرد پایدار و بدون باگ\n"
        f"🔔 آپدیت‌های هفتگی\n"
        f"👥 کامیونیتی فعال و پرانرژی\n"
        f"🚨 پشتیبانی ۲۴ ساعته\n"
        f"🟡 کاملاً رایگان برای همه\n\n"
        f"🐣 فقط کافیه ربات رو به گروهت اضافه کنی...\n"
        f"🌸 بعدش شروع کنی به جوجو جوجو کردن!"
    )


def _guide_text() -> str:
    return (
        f"❓ <b>راهنمای کامل جوجو</b>\n\n"
        f"🐣 <b>میو کردن</b>\n"
        f"دکمه «🐣 جوجو جوجو کن» رو بزن یا تو چت خصوصی مستقیم بنویس «{DEFAULT_PET_NAME}» "
        f"تا {CURRENCY_NAME} بگیری. هر بار میو کنی، بعد از یه مدت استراحت (که با سطح "
        f"بالاتر کمتر میشه) دوباره می‌تونی میو کنی.\n\n"
        f"⭐ <b>سطح و تجربه</b>\n"
        f"هر میو، تجربه اضافه می‌کنه. با رسیدن به آستانه‌ی هر سطح، ارتقا می‌گیری و "
        f"جایزه‌ی نقدی هم دریافت می‌کنی.\n\n"
        f"🏦 <b>بانک</b>\n"
        f"از سطح ۴ به بعد می‌تونی حساب باز کنی، پول واریز/برداشت کنی و سود روزانه بگیری.\n\n"
        f"🎮 <b>بازی‌ها</b>\n"
        f"بسکتبال، بولینگ، دارت و فوتبال - با شرط‌بندی پوینت در مقابل بقیه کاربرا.\n\n"
        f"🛍 <b>مارکت</b>\n"
        f"محصولات مختلف رو با {CURRENCY_NAME} بخر (روزانه حداکثر ۵۰ عدد).\n\n"
        f"🏆 <b>لیدربرد</b>\n"
        f"ببین کی ثروتمندترین، پرفعالیت‌ترین یا بالاسطح‌ترین کاربره."
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    is_new = create_user_if_not_exists(user_id, username)
    bot_info = await message.bot.get_me()

    if is_new:
        text = _welcome_text()
        await message.answer(
            text,
            reply_markup=welcome_inline_kb(bot_info.username),
            parse_mode="HTML",
        )
        # کیبورد اصلی رو هم جدا می‌فرستیم چون reply keyboard و inline keyboard
        # نمیتونن رو یه پیام همزمان باشن
        await message.answer(
            "برای شروع، از منوی پایین استفاده کن 👇",
            reply_markup=main_menu_kb(),
        )
    else:
        user = get_user(user_id)
        await message.answer(
            f"سلام دوباره {user['pet_name']} 🐣 خوش برگشتی!",
            reply_markup=main_menu_kb(),
        )


@router.callback_query(F.data == "show_guide")
async def cb_show_guide(callback: CallbackQuery):
    await callback.message.answer(_guide_text(), parse_mode="HTML")
    await callback.answer()

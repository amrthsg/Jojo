# handlers/start.py
# هندلر /start - ساخت کاربر جدید، پیام معرفی و راهنما
# تنها دکمه‌ی باقی‌مونده «افزودن به گروه» است چون یک لینک خارجی است، نه اکشن داخلی ربات.

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from database.models import create_user_if_not_exists, get_user
from keyboards.main_kb import welcome_inline_kb
from config import CURRENCY_NAME

router = Router()


def _welcome_text() -> str:
    return (
        f"⚡️ <b>ربات سرگرمی جوجویی</b>\n\n"
        f"🐤 یه جوجه بامزه برای گروهت…\n"
        f"کافیه توی گروه جیک جیک کنی تا جیک پوینت بگیری\n\n"
        f"⭐️ جیک پوینت جمع کن و با بقیه رقابت کن\n"
        f"🏆 لیدربرد جوجویی رو فتح کن و پادشاه جوجه‌ ها شو\n\n"
        f"✨ چرا جوجویی ؟\n\n"
        f"⚡️ پاسخگویی فوق‌ العاده سریع\n"
        f"🛠 عملکرد پایدار و بدون باگ\n"
        f"🔄 آپدیت‌ های هفتگی\n"
        f"👥 کامیونیتی فعال و پرانرژی\n"
        f"🚨 پشتیبانی ۲۴ ساعته\n"
        f"🪙 کاملاً رایگان برای همه\n\n"
        f"🐤 کافیه ربات رو به گروهت اضافه کنی…\n"
        f"┘─ بعدش شروع کنی به جیک جیک کردن"
    )


def _guide_text() -> str:
    return (
        f"❓ <b>راهنمای کامل جوجو</b>\n\n"
        f"🐣 <b>جیک کردن</b>\n"
        f"بنویس «جیک جیک» تا {CURRENCY_NAME} بگیری. هر بار جیک کنی، "
        f"بعد از یه مدت استراحت (که با سطح بالاتر کمتر میشه) دوباره می‌تونی جیک کنی.\n\n"
        f"⭐ <b>سطح و تجربه</b>\n"
        f"هر جیک، تجربه اضافه می‌کنه. با رسیدن به آستانه‌ی هر سطح، ارتقا می‌گیری و "
        f"جایزه‌ی نقدی هم دریافت می‌کنی. بنویس «سطح» تا وضعیتت رو ببینی.\n\n"
        f"🏦 <b>بانک</b>\n"
        f"از سطح ۴ به بعد بنویس «بانک» تا حساب باز کنی، پول واریز/برداشت کنی و سود روزانه بگیری.\n\n"
        f"🎮 <b>بازی‌ها</b>\n"
        f"بنویس «بازی» - بسکتبال، بولینگ، دارت و فوتبال با شرط‌بندی پوینت در مقابل بقیه کاربرا.\n\n"
        f"🛍 <b>مارکت</b>\n"
        f"بنویس «مارکت» و محصولات مختلف رو با {CURRENCY_NAME} بخر (روزانه حداکثر ۵۰ عدد).\n\n"
        f"🏆 <b>لیدربرد</b>\n"
        f"بنویس «لیدربرد» تا ببینی کی ثروتمندترین، پرفعالیت‌ترین یا بالاسطح‌ترین کاربره.\n\n"
        f"🪪 <b>پروفایل</b>\n"
        f"بنویس «پروفایل» تا وضعیت کامل جوجوت رو ببینی."
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    create_user_if_not_exists(user_id, username)
    bot_info = await message.bot.get_me()

    await message.answer(
        _welcome_text(),
        reply_markup=welcome_inline_kb(bot_info.username),
        parse_mode="HTML",
    )


@router.message(F.text == "راهنما")
async def handle_guide_text(message: Message):
    await message.answer(_guide_text(), parse_mode="HTML")


@router.callback_query(F.data == "show_guide")
async def cb_show_guide(callback: CallbackQuery):
    await callback.message.answer(_guide_text(), parse_mode="HTML")
    await callback.answer()

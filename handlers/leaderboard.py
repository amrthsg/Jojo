# handlers/leaderboard.py
# لیدربرد - با دکمه شیشه‌ای

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database.models import get_leaderboard
from keyboards.main_kb import leaderboard_menu_kb
from utils.premium_emoji import build_premium_entities
from config import CURRENCY_EMOJI

router = Router()

MEDALS = ["🥇", "🥈", "🥉"]


def _format_leaderboard(rows, title: str):
    lines = [f"🏆 {title}\n"]
    for i, row in enumerate(rows):
        medal = MEDALS[i] if i < 3 else f"{i + 1}."
        # اسم واقعی تلگرام رو ترجیح می‌دیم، وگرنه نام جوجو یا یوزرنیم
        name = row["display_name"] or row["pet_name"] or row["username"] or "ناشناس"
        lines.append(f"{medal} {name} — {row['score']:,} {CURRENCY_EMOJI}")
    if not rows:
        lines.append("هنوز کسی امتیازی نداره!")
    text = "\n".join(lines)
    return build_premium_entities(text, [("🏆", "trophy")])


@router.message(F.text == "لیدربرد")
async def handle_leaderboard_menu(message: Message):
    text = "🏆 لیدربرد جوجو\n\nیکی از لیدربردها رو انتخاب کن:"
    text, entities = build_premium_entities(text, [("🏆", "trophy")])
    await message.answer(text, entities=entities or None, reply_markup=leaderboard_menu_kb())


@router.callback_query(F.data == "lb_meow_points")
async def cb_lb_points(callback: CallbackQuery):
    rows = get_leaderboard("meow_points", limit=10)
    text, entities = _format_leaderboard(rows, "ثروتمندترین‌های جوجو")
    await callback.message.edit_text(text, entities=entities or None, reply_markup=leaderboard_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "lb_exp")
async def cb_lb_exp(callback: CallbackQuery):
    rows = get_leaderboard("exp", limit=10)
    text, entities = _format_leaderboard(rows, "پرفعالیت‌ترین‌های جوجو")
    await callback.message.edit_text(text, entities=entities or None, reply_markup=leaderboard_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "lb_level")
async def cb_lb_level(callback: CallbackQuery):
    rows = get_leaderboard("level", limit=10)
    text, entities = _format_leaderboard(rows, "بالاسطح‌ترین‌های جوجو")
    await callback.message.edit_text(text, entities=entities or None, reply_markup=leaderboard_menu_kb())
    await callback.answer()

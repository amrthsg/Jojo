# handlers/leaderboard.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database.models import get_leaderboard
from keyboards.main_kb import leaderboard_menu_kb
from config import CURRENCY_EMOJI

router = Router()

MEDALS = ["🥇", "🥈", "🥉"]


def _format_leaderboard(rows, title: str) -> str:
    lines = [f"🏆 <b>{title}</b>\n"]
    for i, row in enumerate(rows):
        medal = MEDALS[i] if i < 3 else f"{i + 1}."
        name = row["pet_name"] or row["username"] or "ناشناس"
        lines.append(f"{medal} {name} — {row['score']:,} {CURRENCY_EMOJI}")
    if not rows:
        lines.append("هنوز کسی امتیازی نداره!")
    return "\n".join(lines)


@router.message(F.text == "🏆 لیدربرد")
async def handle_leaderboard_menu(message: Message):
    await message.answer(
        "🏆 کدوم لیدربرد رو میخوای ببینی؟",
        reply_markup=leaderboard_menu_kb(),
    )


@router.callback_query(F.data == "lb_meow_points")
async def cb_lb_points(callback: CallbackQuery):
    rows = get_leaderboard("meow_points", limit=10)
    text = _format_leaderboard(rows, "ثروتمندترین‌های جوجو")
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "lb_exp")
async def cb_lb_exp(callback: CallbackQuery):
    rows = get_leaderboard("exp", limit=10)
    text = _format_leaderboard(rows, "پرسر و صداترین‌های جوجو")
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "lb_level")
async def cb_lb_level(callback: CallbackQuery):
    rows = get_leaderboard("level", limit=10)
    text = _format_leaderboard(rows, "بالاترین سطح‌های جوجو")
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

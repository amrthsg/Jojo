# handlers/leaderboard.py
# لیدربرد - کاملاً متنی بدون هیچ دکمه‌ای

from aiogram import Router, F
from aiogram.types import Message

from database.models import get_leaderboard
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


@router.message(F.text == "لیدربرد")
async def handle_leaderboard_menu(message: Message):
    await message.answer(
        "🏆 <b>لیدربرد جوجو</b>\n\n"
        "بنویس «لیدربرد پوینت» برای ثروتمندترین‌ها\n"
        "بنویس «لیدربرد فعالیت» برای پرفعالیت‌ترین‌ها\n"
        "بنویس «لیدربرد سطح» برای بالاسطح‌ترین‌ها",
        parse_mode="HTML",
    )


@router.message(F.text.in_({"لیدربرد پوینت", "لیدربرد ثروت"}))
async def handle_lb_points(message: Message):
    rows = get_leaderboard("meow_points", limit=10)
    text = _format_leaderboard(rows, "ثروتمندترین‌های جوجو")
    await message.answer(text, parse_mode="HTML")


@router.message(F.text.in_({"لیدربرد فعالیت", "لیدربرد تجربه"}))
async def handle_lb_exp(message: Message):
    rows = get_leaderboard("exp", limit=10)
    text = _format_leaderboard(rows, "پرفعالیت‌ترین‌های جوجو")
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "لیدربرد سطح")
async def handle_lb_level(message: Message):
    rows = get_leaderboard("level", limit=10)
    text = _format_leaderboard(rows, "بالاسطح‌ترین‌های جوجو")
    await message.answer(text, parse_mode="HTML")

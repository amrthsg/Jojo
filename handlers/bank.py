# handlers/bank.py
# هندلر بخش بانک جوجو - کاملاً متنی، بدون هیچ دکمه‌ای

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.models import get_user, add_meow_points
from database.bank_models import (
    get_bank_account,
    open_bank_account,
    deposit_to_bank,
    withdraw_from_bank,
    calculate_and_apply_interest,
    card_to_card_transfer,
    calculate_transfer_fee,
    change_card_number,
)
from config import BANK_MIN_LEVEL, BANK_ACCOUNT_OPEN_COST, CURRENCY_EMOJI, CARD_NUMBER_CHANGE_COST

router = Router()


class BankStates(StatesGroup):
    waiting_deposit_amount = State()
    waiting_withdraw_amount = State()
    waiting_transfer_card = State()
    waiting_transfer_amount = State()


def _bank_help_text() -> str:
    return (
        "🏦 <b>راهنمای بانک</b>\n\n"
        "بنویس «بانک» برای دیدن موجودی\n"
        "بنویس «واریز {مبلغ}» مثلاً: واریز 500\n"
        "بنویس «برداشت {مبلغ}» مثلاً: برداشت 500\n"
        "بنویس «انتقال {شماره حساب} {مبلغ}»\n"
        "بنویس «تغییر شماره حساب»"
    )


@router.message(F.text == "بانک")
async def handle_bank_menu(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user:
        await message.answer("اول باید /start بزنی 🐤")
        return

    if user["level"] < BANK_MIN_LEVEL:
        await message.answer(
            f"🏦 برای افتتاح حساب بانکی باید حداقل سطح {BANK_MIN_LEVEL} باشی."
        )
        return

    account = get_bank_account(user_id)
    if not account:
        if user["meow_points"] < BANK_ACCOUNT_OPEN_COST:
            await message.answer(
                f"برای افتتاح حساب بانکی به {BANK_ACCOUNT_OPEN_COST:,} {CURRENCY_EMOJI} نیاز داری."
            )
            return
        add_meow_points(user_id, -BANK_ACCOUNT_OPEN_COST)
        card_number = open_bank_account(user_id)
        await message.answer(
            f"🎉 حساب بانکی باز شد!\n💳 شماره حساب شما: <code>{card_number}</code>\n\n"
            f"{_bank_help_text()}",
            parse_mode="HTML",
        )
        return

    interest = calculate_and_apply_interest(user_id)
    account = get_bank_account(user_id)  # رفرش بعد از سود احتمالی

    text = (
        f"🏦 <b>بانک جوجو</b>\n\n"
        f"💳 شماره حساب: <code>{account['card_number']}</code>\n"
        f"💰 موجودی: {account['balance']:,} {CURRENCY_EMOJI}\n"
    )
    if interest:
        text += f"\n🎉 سود روزانه {interest:,} {CURRENCY_EMOJI} به حسابت اضافه شد!\n"

    text += f"\n{_bank_help_text()}"

    await message.answer(text, parse_mode="HTML")


@router.message(F.text.regexp(r"^واریز\s+(\d+)$"))
async def handle_deposit_command(message: Message):
    amount = int(message.text.split()[1])
    user = get_user(message.from_user.id)

    if not user:
        await message.answer("اول باید /start بزنی 🐤")
        return

    account = get_bank_account(message.from_user.id)
    if not account:
        await message.answer("❌ اول باید بنویسی «بانک» تا حساب باز کنی.")
        return

    if amount <= 0 or amount > user["meow_points"]:
        await message.answer("❌ موجودی کافی نیست.")
        return

    deposit_to_bank(message.from_user.id, amount)
    await message.answer(f"✅ {amount:,} {CURRENCY_EMOJI} به بانک واریز شد.")


@router.message(F.text.regexp(r"^برداشت\s+(\d+)$"))
async def handle_withdraw_command(message: Message):
    amount = int(message.text.split()[1])
    account = get_bank_account(message.from_user.id)

    if not account:
        await message.answer("❌ اول باید بنویسی «بانک» تا حساب باز کنی.")
        return

    if amount <= 0 or amount > account["balance"]:
        await message.answer("❌ موجودی بانک کافی نیست.")
        return

    withdraw_from_bank(message.from_user.id, amount)
    await message.answer(f"✅ {amount:,} {CURRENCY_EMOJI} از بانک برداشت شد.")


@router.message(F.text.regexp(r"^انتقال\s+(\S+)\s+(\d+)$"))
async def handle_transfer_command(message: Message):
    parts = message.text.split()
    to_card = parts[1]
    amount = int(parts[2])

    account = get_bank_account(message.from_user.id)
    if not account:
        await message.answer("❌ اول باید بنویسی «بانک» تا حساب باز کنی.")
        return

    fee = calculate_transfer_fee(amount)
    success, msg = card_to_card_transfer(message.from_user.id, to_card, amount)

    if success:
        await message.answer(f"✅ {amount:,} {CURRENCY_EMOJI} با کارمزد {fee:,} انتقال یافت.")
    else:
        await message.answer(f"❌ {msg}")


@router.message(F.text == "تغییر شماره حساب")
async def handle_change_card_number(message: Message):
    success, msg, new_number = change_card_number(message.from_user.id, CARD_NUMBER_CHANGE_COST)
    if success:
        await message.answer(f"✅ شماره حساب جدید: <code>{new_number}</code>", parse_mode="HTML")
    else:
        await message.answer(f"❌ {msg}")

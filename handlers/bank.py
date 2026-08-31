# handlers/bank.py
# هندلر بخش بانک میویی

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
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
from keyboards.main_kb import bank_menu_kb
from config import BANK_MIN_LEVEL, BANK_ACCOUNT_OPEN_COST, CURRENCY_EMOJI, CARD_NUMBER_CHANGE_COST

router = Router()


class BankStates(StatesGroup):
    waiting_deposit_amount = State()
    waiting_withdraw_amount = State()
    waiting_transfer_card = State()
    waiting_transfer_amount = State()


@router.message(F.text == "🏦 بانک")
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
            f"🎉 حساب بانکی باز شد!\n💳 شماره حساب شما: <code>{card_number}</code>",
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
        text += f"\n🎉 سود روزانه {interest:,} {CURRENCY_EMOJI} به حسابت اضافه شد!"

    await message.answer(text, reply_markup=bank_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "bank_balance")
async def cb_bank_balance(callback: CallbackQuery):
    account = get_bank_account(callback.from_user.id)
    if not account:
        await callback.answer("حساب بانکی نداری", show_alert=True)
        return
    await callback.answer(f"موجودی: {account['balance']:,} {CURRENCY_EMOJI}", show_alert=True)


@router.callback_query(F.data == "bank_deposit")
async def cb_bank_deposit(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("💰 چه مقدار می‌خوای به بانک واریز کنی؟ (فقط عدد بفرست)")
    await state.set_state(BankStates.waiting_deposit_amount)
    await callback.answer()


@router.message(BankStates.waiting_deposit_amount)
async def process_deposit(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ لطفاً فقط عدد بفرست.")
        return

    amount = int(message.text)
    user = get_user(message.from_user.id)

    if amount <= 0 or amount > user["meow_points"]:
        await message.answer("❌ موجودی کافی نیست.")
        await state.clear()
        return

    deposit_to_bank(message.from_user.id, amount)
    await message.answer(f"✅ {amount:,} {CURRENCY_EMOJI} به بانک واریز شد.")
    await state.clear()


@router.callback_query(F.data == "bank_withdraw")
async def cb_bank_withdraw(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("💸 چه مقدار می‌خوای از بانک برداشت کنی؟ (فقط عدد بفرست)")
    await state.set_state(BankStates.waiting_withdraw_amount)
    await callback.answer()


@router.message(BankStates.waiting_withdraw_amount)
async def process_withdraw(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ لطفاً فقط عدد بفرست.")
        return

    amount = int(message.text)
    account = get_bank_account(message.from_user.id)

    if not account or amount <= 0 or amount > account["balance"]:
        await message.answer("❌ موجودی بانک کافی نیست.")
        await state.clear()
        return

    withdraw_from_bank(message.from_user.id, amount)
    await message.answer(f"✅ {amount:,} {CURRENCY_EMOJI} از بانک برداشت شد.")
    await state.clear()


@router.callback_query(F.data == "bank_transfer")
async def cb_bank_transfer(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("💳 شماره حساب مقصد رو بفرست:")
    await state.set_state(BankStates.waiting_transfer_card)
    await callback.answer()


@router.message(BankStates.waiting_transfer_card)
async def process_transfer_card(message: Message, state: FSMContext):
    await state.update_data(to_card=message.text.strip())
    await message.answer("💰 حالا مبلغ انتقال رو بفرست:")
    await state.set_state(BankStates.waiting_transfer_amount)


@router.message(BankStates.waiting_transfer_amount)
async def process_transfer_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ لطفاً فقط عدد بفرست.")
        return

    amount = int(message.text)
    data = await state.get_data()
    to_card = data.get("to_card")

    fee = calculate_transfer_fee(amount)
    success, msg = card_to_card_transfer(message.from_user.id, to_card, amount)

    if success:
        await message.answer(
            f"✅ {amount:,} {CURRENCY_EMOJI} با کارمزد {fee:,} انتقال یافت."
        )
    else:
        await message.answer(f"❌ {msg}")

    await state.clear()


@router.callback_query(F.data == "bank_change_number")
async def cb_change_card_number(callback: CallbackQuery):
    success, msg, new_number = change_card_number(callback.from_user.id, CARD_NUMBER_CHANGE_COST)
    if success:
        await callback.message.answer(f"✅ شماره حساب جدید: <code>{new_number}</code>", parse_mode="HTML")
    else:
        await callback.message.answer(f"❌ {msg}")
    await callback.answer()

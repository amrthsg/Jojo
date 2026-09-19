# handlers/bank.py
# هندلر بخش بانک جوجو - نسخه کامل با وام، قفل بانک، تراکنش‌ها و دکمه‌های درصدی

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
    preview_next_interest,
    card_to_card_transfer,
    calculate_transfer_fee,
    change_card_number,
    toggle_bank_lock,
    get_bank_transactions,
    get_active_loan,
    request_loan,
    pay_loan_installment,
)
from keyboards.main_kb import (
    bank_menu_kb,
    bank_percent_kb,
    bank_transfer_percent_kb,
    bank_lock_confirm_kb,
    cancel_kb,
)
from config import (
    BANK_MIN_LEVEL,
    BANK_ACCOUNT_OPEN_COST,
    CURRENCY_EMOJI,
    CARD_NUMBER_CHANGE_COST,
    LOAN_MAX_AMOUNT,
    LOAN_FEE_PERCENT,
    LOAN_INSTALLMENTS_COUNT,
    LOAN_INSTALLMENT_INTERVAL_SECONDS,
)
from utils.leveling import format_time

router = Router()


class BankStates(StatesGroup):
    waiting_deposit_amount = State()
    waiting_withdraw_amount = State()
    waiting_transfer_card = State()
    waiting_transfer_amount = State()
    waiting_loan_amount = State()


def _format_bank_text(user, account, interest_applied: int) -> str:
    preview = preview_next_interest(user["user_id"])
    base_balance, interest, balance_after, remaining_seconds = preview

    text = (
        f"🏦 <b>بانک جوجو</b>\n\n"
        f"💳 شماره کارت: <code>{account['card_number']}</code>\n"
        f"👤 به نام: {user['display_name'] or user['pet_name']}\n\n"
        f"🏆 موجودی حساب: {account['balance']:,} {CURRENCY_EMOJI}\n\n"
        f"🤑 <b>سود بانکی</b>\n"
        f"🌸 درصد سود: ۳٪ روزانه\n"
        f"⬇️ کل سود دریافتی: {account['total_interest_earned']:,} {CURRENCY_EMOJI}\n"
        f"⏳ واریز بعدی: {format_time(remaining_seconds)}\n\n"
        f"⚡️ <b>محاسبه سود روزانه</b>\n"
        f"— موجودی مبنا: {base_balance:,}\n"
        f"— سود قابل دریافت: +{interest:,}\n"
        f"— موجودی بعد از سود: {balance_after:,}\n"
    )

    if interest_applied:
        text += f"\n🎉 سود {interest_applied:,} {CURRENCY_EMOJI} همین الان به حسابت اضافه شد!\n"

    return text


async def _send_bank_menu(message_or_callback, user_id: int, edit: bool = False):
    user = get_user(user_id)
    if not user:
        text = "اول باید /start بزنی 🐤"
        target = message_or_callback.message if edit else message_or_callback
        await (target.edit_text(text) if edit else target.answer(text))
        return

    if user["level"] < BANK_MIN_LEVEL:
        text = f"🏦 برای افتتاح حساب بانکی باید حداقل سطح {BANK_MIN_LEVEL} باشی."
        target = message_or_callback.message if edit else message_or_callback
        await (target.edit_text(text) if edit else target.answer(text))
        return

    account = get_bank_account(user_id)
    if not account:
        if user["meow_points"] < BANK_ACCOUNT_OPEN_COST:
            text = f"برای افتتاح حساب بانکی به {BANK_ACCOUNT_OPEN_COST:,} {CURRENCY_EMOJI} نیاز داری."
            target = message_or_callback.message if edit else message_or_callback
            await (target.edit_text(text) if edit else target.answer(text))
            return
        add_meow_points(user_id, -BANK_ACCOUNT_OPEN_COST)
        card_number = open_bank_account(user_id)
        text = f"🎉 حساب بانکی باز شد!\n💳 شماره حساب شما: <code>{card_number}</code>"
        if edit:
            await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=bank_menu_kb())
        else:
            await message_or_callback.answer(text, parse_mode="HTML", reply_markup=bank_menu_kb())
        return

    # چک و کسر خودکار قسط وام، اگه سررسید شده باشه
    paid, deducted, loan_msg = pay_loan_installment(user_id, LOAN_INSTALLMENT_INTERVAL_SECONDS)

    interest_applied = calculate_and_apply_interest(user_id)
    account = get_bank_account(user_id)  # رفرش بعد از سود/قسط احتمالی

    text = _format_bank_text(user, account, interest_applied)
    if paid:
        text += f"\n💸 {loan_msg}\n"

    if edit:
        await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=bank_menu_kb())
    else:
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=bank_menu_kb())


@router.message(F.text == "بانک")
async def handle_bank_menu(message: Message):
    await _send_bank_menu(message, message.from_user.id)


@router.callback_query(F.data == "bank_balance")
async def cb_bank_balance(callback: CallbackQuery):
    await _send_bank_menu(callback, callback.from_user.id, edit=True)
    await callback.answer()


# ---------------- واریز / برداشت با دکمه درصدی ----------------

@router.callback_query(F.data == "bank_deposit")
async def cb_bank_deposit(callback: CallbackQuery):
    await callback.message.edit_text(
        "⬆️ چند درصد از موجودی کیف پولت رو می‌خوای واریز کنی؟",
        reply_markup=bank_percent_kb("deposit"),
    )
    await callback.answer()


@router.callback_query(F.data == "bank_withdraw")
async def cb_bank_withdraw(callback: CallbackQuery):
    await callback.message.edit_text(
        "⬇️ چند درصد از موجودی بانکت رو می‌خوای برداشت کنی؟",
        reply_markup=bank_percent_kb("withdraw"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bankpct_"))
async def cb_bank_percent(callback: CallbackQuery, state: FSMContext):
    _, action, pct = callback.data.split("_")
    user_id = callback.from_user.id

    if pct == "custom":
        prompt = "💰 چه مقدار می‌خوای واریز کنی؟" if action == "deposit" else "💸 چه مقدار می‌خوای برداشت کنی؟"
        await callback.message.edit_text(prompt, reply_markup=cancel_kb())
        await state.update_data(bank_action=action)
        await state.set_state(
            BankStates.waiting_deposit_amount if action == "deposit" else BankStates.waiting_withdraw_amount
        )
        await callback.answer()
        return

    percent = int(pct)
    user = get_user(user_id)
    account = get_bank_account(user_id)

    if action == "deposit":
        base = user["meow_points"] if user else 0
        amount = base * percent // 100
        if amount <= 0:
            await callback.answer("❌ موجودی کافی نیست.", show_alert=True)
            return
        deposit_to_bank(user_id, amount)
        await callback.answer(f"✅ {amount:,} {CURRENCY_EMOJI} واریز شد.", show_alert=True)
    else:
        base = account["balance"] if account else 0
        amount = base * percent // 100
        if amount <= 0:
            await callback.answer("❌ موجودی بانک کافی نیست.", show_alert=True)
            return
        withdraw_from_bank(user_id, amount)
        await callback.answer(f"✅ {amount:,} {CURRENCY_EMOJI} برداشت شد.", show_alert=True)

    await _send_bank_menu(callback, user_id, edit=True)


@router.message(BankStates.waiting_deposit_amount)
async def process_deposit_custom(message: Message, state: FSMContext):
    from utils.amount_parser import parse_amount

    amount = parse_amount(message.text.strip())
    if amount is None or amount <= 0:
        await message.answer("❌ مبلغ نامعتبره. یه عدد بفرست، مثلاً 500000 یا 500k یا 500کا")
        return

    user = get_user(message.from_user.id)

    if amount > user["meow_points"]:
        await message.answer("❌ موجودی کافی نیست.")
        await state.clear()
        return

    deposit_to_bank(message.from_user.id, amount)
    await message.answer(f"✅ {amount:,} {CURRENCY_EMOJI} به بانک واریز شد.")
    await state.clear()


@router.message(BankStates.waiting_withdraw_amount)
async def process_withdraw_custom(message: Message, state: FSMContext):
    from utils.amount_parser import parse_amount

    amount = parse_amount(message.text.strip())
    if amount is None or amount <= 0:
        await message.answer("❌ مبلغ نامعتبره. یه عدد بفرست، مثلاً 500000 یا 500k یا 500کا")
        return

    account = get_bank_account(message.from_user.id)

    if not account or amount > account["balance"]:
        await message.answer("❌ موجودی بانک کافی نیست.")
        await state.clear()
        return

    withdraw_from_bank(message.from_user.id, amount)
    await message.answer(f"✅ {amount:,} {CURRENCY_EMOJI} از بانک برداشت شد.")
    await state.clear()


# ---------------- کارت به کارت با دکمه درصدی ----------------

@router.callback_query(F.data == "bank_transfer")
async def cb_bank_transfer(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("💳 شماره حساب مقصد رو بفرست:", reply_markup=cancel_kb())
    await state.set_state(BankStates.waiting_transfer_card)
    await callback.answer()


@router.message(BankStates.waiting_transfer_card)
async def process_transfer_card(message: Message, state: FSMContext):
    to_card = message.text.strip()
    await state.update_data(to_card=to_card)
    await message.answer(
        "💰 چند درصد از موجودی بانکت رو می‌خوای انتقال بدی؟",
        reply_markup=bank_transfer_percent_kb(),
    )
    await state.set_state(BankStates.waiting_transfer_amount)


@router.callback_query(F.data.startswith("transferpct_"))
async def cb_transfer_percent(callback: CallbackQuery, state: FSMContext):
    pct = callback.data.replace("transferpct_", "")
    data = await state.get_data()
    to_card = data.get("to_card")

    if pct == "custom":
        await callback.message.edit_text("✏️ مبلغ دلخواه رو بفرست:")
        await callback.answer()
        return

    account = get_bank_account(callback.from_user.id)
    if not account:
        await callback.answer("❌ حساب بانکی نداری.", show_alert=True)
        await state.clear()
        return

    percent = int(pct)
    amount = account["balance"] * percent // 100

    if amount <= 0:
        await callback.answer("❌ موجودی کافی نیست.", show_alert=True)
        return

    fee = calculate_transfer_fee(amount)
    success, msg = card_to_card_transfer(callback.from_user.id, to_card, amount)

    if success:
        await callback.message.edit_text(f"✅ {amount:,} {CURRENCY_EMOJI} با کارمزد {fee:,} انتقال یافت.")
    else:
        await callback.message.edit_text(f"❌ {msg}")

    await state.clear()
    await callback.answer()


@router.message(BankStates.waiting_transfer_amount)
async def process_transfer_amount_custom(message: Message, state: FSMContext):
    from utils.amount_parser import parse_amount

    amount = parse_amount(message.text.strip())
    if amount is None or amount <= 0:
        await message.answer("❌ مبلغ نامعتبره. یه عدد بفرست، مثلاً 500000 یا 500k یا 500کا")
        return

    data = await state.get_data()
    to_card = data.get("to_card")

    fee = calculate_transfer_fee(amount)
    success, msg = card_to_card_transfer(message.from_user.id, to_card, amount)

    if success:
        await message.answer(f"✅ {amount:,} {CURRENCY_EMOJI} با کارمزد {fee:,} انتقال یافت.")
    else:
        await message.answer(f"❌ {msg}")

    await state.clear()


# ---------------- تغییر شماره حساب ----------------

@router.callback_query(F.data == "bank_change_number")
async def cb_change_card_number(callback: CallbackQuery):
    success, msg, new_number = change_card_number(callback.from_user.id, CARD_NUMBER_CHANGE_COST)
    if success:
        await callback.message.answer(f"✅ شماره حساب جدید: <code>{new_number}</code>", parse_mode="HTML")
    else:
        await callback.message.answer(f"❌ {msg}")
    await callback.answer()


# ---------------- تراکنش‌ها ----------------

@router.callback_query(F.data == "bank_transactions")
async def cb_bank_transactions(callback: CallbackQuery):
    user_id = callback.from_user.id
    txs = get_bank_transactions(user_id, limit=10)

    if not txs:
        await callback.answer("هنوز هیچ تراکنش کارت‌به‌کارتی نداری.", show_alert=True)
        return

    lines = ["📜 <b>تراکنش‌های بانکی</b>\n"]
    for tx in txs:
        direction = "⬆️ ارسال" if tx["from_user"] == user_id else "⬇️ دریافت"
        lines.append(f"{direction} — {tx['amount']:,} {CURRENCY_EMOJI} (کارمزد {tx['fee']:,})")

    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


# ---------------- قفل بانک ----------------

@router.callback_query(F.data == "bank_lock")
async def cb_bank_lock(callback: CallbackQuery):
    account = get_bank_account(callback.from_user.id)
    if not account:
        await callback.answer("❌ حساب بانکی نداری.", show_alert=True)
        return

    status = "باز" if not account["is_locked"] else "قفل"
    action_text = "قفل کردن" if not account["is_locked"] else "باز کردن"

    await callback.message.edit_text(
        f"🔒 نمایش عمومی بانک الان {status} است.\n\n"
        f"با {action_text} بانک، فقط خودتان و تیم مدیریت جوجو می‌توانند موجودی بانک را ببینند.\n\n"
        f"آیا مطمئن هستید؟",
        reply_markup=bank_lock_confirm_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "bank_lock_confirm")
async def cb_bank_lock_confirm(callback: CallbackQuery):
    account = get_bank_account(callback.from_user.id)
    if not account:
        await callback.answer("❌ حساب بانکی نداری.", show_alert=True)
        return

    new_state = not bool(account["is_locked"])
    toggle_bank_lock(callback.from_user.id, new_state)

    status_text = "قفل شد 🔒" if new_state else "باز شد 🔓"
    await callback.message.edit_text(f"✅ نمایش عمومی بانک {status_text}")
    await callback.answer()


@router.callback_query(F.data == "bank_lock_cancel")
async def cb_bank_lock_cancel(callback: CallbackQuery):
    await _send_bank_menu(callback, callback.from_user.id, edit=True)
    await callback.answer()


# ---------------- وام بانکی ----------------

@router.callback_query(F.data == "bank_loan_request")
async def cb_loan_request(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    active_loan = get_active_loan(user_id)

    if active_loan:
        remaining_installments = active_loan["installments_total"] - active_loan["installments_paid"]
        await callback.message.edit_text(
            f"⚠️ شما یک وام فعال دارید.\n\n"
            f"💰 مانده بازپرداخت: {active_loan['remaining_amount']:,} {CURRENCY_EMOJI}\n"
            f"📋 اقساط باقی‌مانده: {remaining_installments} از {active_loan['installments_total']}\n"
            f"💳 مبلغ هر قسط: {active_loan['installment_amount']:,} {CURRENCY_EMOJI}",
            reply_markup=bank_menu_kb(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"➕ <b>وام بانک جوجو</b>\n\n"
        f"مقدار مبلغ وام موردنظر را وارد کنید.\n"
        f"❗️ حداکثر درخواست: {LOAN_MAX_AMOUNT:,} {CURRENCY_EMOJI}\n"
        f"⏳ مدت بازپرداخت: {LOAN_INSTALLMENTS_COUNT} روز، در {LOAN_INSTALLMENTS_COUNT} قسط روزانه\n"
        f"⬆️ کارمزد بازپرداخت: {LOAN_FEE_PERCENT}٪\n",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await state.set_state(BankStates.waiting_loan_amount)
    await callback.answer()


@router.message(BankStates.waiting_loan_amount)
async def process_loan_amount(message: Message, state: FSMContext):
    from utils.amount_parser import parse_amount

    amount = parse_amount(message.text.strip())
    if amount is None or amount <= 0:
        await message.answer("❌ مبلغ نامعتبره. یه عدد بفرست، مثلاً 500000 یا 500k یا 500کا")
        return

    if amount > LOAN_MAX_AMOUNT:
        await message.answer(f"❌ مبلغ باید بین ۱ تا {LOAN_MAX_AMOUNT:,} باشد.")
        await state.clear()
        return

    account = get_bank_account(message.from_user.id)
    if not account:
        await message.answer("❌ اول باید بنویسی «بانک» تا حساب باز کنی.")
        await state.clear()
        return

    success, msg, loan = request_loan(
        message.from_user.id, amount, LOAN_FEE_PERCENT, LOAN_INSTALLMENTS_COUNT
    )

    if success:
        await message.answer(
            f"✅ {msg}\n\n"
            f"💳 مبلغ هر قسط: {loan['installment_amount']:,} {CURRENCY_EMOJI}\n"
            f"📋 تعداد اقساط: {loan['installments_total']}\n"
            f"⏳ هر {LOAN_INSTALLMENT_INTERVAL_SECONDS // 3600} ساعت یک قسط به‌صورت خودکار از کیف پولت کسر میشه."
        )
    else:
        await message.answer(f"❌ {msg}")

    await state.clear()


@router.callback_query(F.data == "cancel_fsm")
async def cb_cancel_fsm(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ عملیات لغو شد.")
    await callback.answer()

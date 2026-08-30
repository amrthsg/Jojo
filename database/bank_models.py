# database/bank_models.py
# منطق بانک میویی: افتتاح حساب، سود روزانه، واریز/برداشت، کارت‌به‌کارت

import time
import random
from database.db import get_connection
from config import (
    BANK_DAILY_INTEREST_RATE,
    BANK_DAILY_INTEREST_CAP,
    CARD_TRANSFER_FEE_PERCENT,
    CARD_TRANSFER_MIN_FEE,
    CARD_TRANSFER_MAX_FEE,
)


def get_bank_account(user_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM bank_accounts WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row


def _generate_card_number():
    """شماره حساب ۱۲ رقمی تصادفی و یکتا"""
    while True:
        number = "".join(str(random.randint(0, 9)) for _ in range(12))
        conn = get_connection()
        exists = conn.execute(
            "SELECT 1 FROM bank_accounts WHERE card_number = ?", (number,)
        ).fetchone()
        conn.close()
        if not exists:
            return number


def open_bank_account(user_id: int):
    """حساب بانکی جدید با موجودی صفر و شماره حساب تصادفی می‌سازه"""
    card_number = _generate_card_number()
    conn = get_connection()
    conn.execute(
        """INSERT INTO bank_accounts (user_id, balance, card_number, last_interest_time)
           VALUES (?, 0, ?, ?)""",
        (user_id, card_number, int(time.time())),
    )
    conn.commit()
    conn.close()
    return card_number


def deposit_to_bank(user_id: int, amount: int):
    """از کیف پول (meow_points) به بانک واریز می‌کنه"""
    conn = get_connection()
    conn.execute(
        "UPDATE users SET meow_points = meow_points - ? WHERE user_id = ?",
        (amount, user_id),
    )
    conn.execute(
        "UPDATE bank_accounts SET balance = balance + ? WHERE user_id = ?",
        (amount, user_id),
    )
    conn.commit()
    conn.close()


def withdraw_from_bank(user_id: int, amount: int):
    """از بانک به کیف پول برداشت می‌کنه"""
    conn = get_connection()
    conn.execute(
        "UPDATE bank_accounts SET balance = balance - ? WHERE user_id = ?",
        (amount, user_id),
    )
    conn.execute(
        "UPDATE users SET meow_points = meow_points + ? WHERE user_id = ?",
        (amount, user_id),
    )
    conn.commit()
    conn.close()


def calculate_and_apply_interest(user_id: int):
    """
    اگه ۲۴ ساعت از آخرین سود گذشته باشه، سود جدید رو حساب و اعمال می‌کنه.
    خروجی: مقدار سودی که اضافه شد (0 اگه هنوز وقتش نشده)
    """
    account = get_bank_account(user_id)
    if not account:
        return 0

    now = int(time.time())
    elapsed = now - account["last_interest_time"]

    if elapsed < 24 * 3600:
        return 0

    # چند دوره ۲۴ ساعته گذشته (اگه کاربر مدتیه نیومده)
    periods = elapsed // (24 * 3600)
    balance = account["balance"]
    total_interest = 0

    for _ in range(periods):
        interest = min(int(balance * BANK_DAILY_INTEREST_RATE), BANK_DAILY_INTEREST_CAP)
        balance += interest
        total_interest += interest

    new_interest_time = account["last_interest_time"] + periods * 24 * 3600

    conn = get_connection()
    conn.execute(
        "UPDATE bank_accounts SET balance = ?, last_interest_time = ? WHERE user_id = ?",
        (balance, new_interest_time, user_id),
    )
    conn.commit()
    conn.close()

    return total_interest


def calculate_transfer_fee(amount: int):
    fee = int(amount * CARD_TRANSFER_FEE_PERCENT / 100)
    fee = max(CARD_TRANSFER_MIN_FEE, min(fee, CARD_TRANSFER_MAX_FEE))
    return fee


def card_to_card_transfer(from_user: int, to_card_number: str, amount: int):
    """
    انتقال مستقیم بین حساب‌های بانکی با کارمزد.
    خروجی: (success: bool, message: str)
    """
    conn = get_connection()
    to_account = conn.execute(
        "SELECT * FROM bank_accounts WHERE card_number = ?", (to_card_number,)
    ).fetchone()

    if not to_account:
        conn.close()
        return False, "شماره حساب مقصد پیدا نشد"

    from_account = conn.execute(
        "SELECT * FROM bank_accounts WHERE user_id = ?", (from_user,)
    ).fetchone()

    if not from_account:
        conn.close()
        return False, "شما حساب بانکی ندارید"

    fee = calculate_transfer_fee(amount)
    total_deduction = amount + fee

    if from_account["balance"] < total_deduction:
        conn.close()
        return False, "موجودی کافی نیست"

    conn.execute(
        "UPDATE bank_accounts SET balance = balance - ? WHERE user_id = ?",
        (total_deduction, from_user),
    )
    conn.execute(
        "UPDATE bank_accounts SET balance = balance + ? WHERE user_id = ?",
        (amount, to_account["user_id"]),
    )
    conn.execute(
        """INSERT INTO transactions (from_user, to_user, amount, fee, tx_type)
           VALUES (?, ?, ?, ?, 'card_transfer')""",
        (from_user, to_account["user_id"], amount, fee),
    )
    conn.commit()
    conn.close()
    return True, f"انتقال موفق. کارمزد: {fee}"


def change_card_number(user_id: int, cost: int):
    account = get_bank_account(user_id)
    if not account:
        return False, "حساب بانکی ندارید", None

    now = int(time.time())
    from config import CARD_NUMBER_CHANGE_COOLDOWN
    if now - account["last_card_change"] < CARD_NUMBER_CHANGE_COOLDOWN:
        remaining = CARD_NUMBER_CHANGE_COOLDOWN - (now - account["last_card_change"])
        return False, f"باید {remaining // 3600} ساعت دیگر صبر کنید", None

    new_number = _generate_card_number()
    conn = get_connection()
    conn.execute(
        "UPDATE bank_accounts SET card_number = ?, last_card_change = ? WHERE user_id = ?",
        (new_number, now, user_id),
    )
    conn.execute(
        "UPDATE users SET meow_points = meow_points - ? WHERE user_id = ?",
        (cost, user_id),
    )
    conn.commit()
    conn.close()
    return True, "شماره حساب تغییر کرد", new_number

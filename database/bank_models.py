# database/bank_models.py
# منطق بانک جوجو: افتتاح حساب، سود روزانه، واریز/برداشت، کارت‌به‌کارت

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
        """UPDATE bank_accounts
           SET balance = ?, last_interest_time = ?, total_interest_earned = total_interest_earned + ?
           WHERE user_id = ?""",
        (balance, new_interest_time, total_interest, user_id),
    )
    conn.commit()
    conn.close()

    return total_interest


def preview_next_interest(user_id: int):
    """
    محاسبه‌ی پیش‌نمایش سود بعدی، بدون اینکه واقعاً اعمالش کنه.
    برای نمایش تو صفحه‌ی بانک استفاده میشه.
    خروجی: (موجودی فعلی، سود قابل دریافت، موجودی بعد از سود، ثانیه‌های باقی‌مانده تا واریز بعدی)
    """
    account = get_bank_account(user_id)
    if not account:
        return None

    now = int(time.time())
    elapsed = now - account["last_interest_time"]
    remaining = max(0, 24 * 3600 - elapsed)

    interest = min(int(account["balance"] * BANK_DAILY_INTEREST_RATE), BANK_DAILY_INTEREST_CAP)
    balance_after = account["balance"] + interest

    return account["balance"], interest, balance_after, remaining


def toggle_bank_lock(user_id: int, locked: bool):
    """قفل/بازکردن نمایش عمومی موجودی بانکی کاربر"""
    conn = get_connection()
    conn.execute(
        "UPDATE bank_accounts SET is_locked = ? WHERE user_id = ?",
        (1 if locked else 0, user_id),
    )
    conn.commit()
    conn.close()


def get_bank_transactions(user_id: int, limit: int = 10):
    """
    آخرین تراکنش‌های کارت‌به‌کارت که این کاربر توشون فرستنده یا گیرنده بوده.
    """
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM transactions
           WHERE (from_user = ? OR to_user = ?) AND tx_type = 'card_transfer'
           ORDER BY timestamp DESC
           LIMIT ?""",
        (user_id, user_id, limit),
    ).fetchall()
    conn.close()
    return rows


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


# ---------------- وام بانکی ----------------

def get_active_loan(user_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM bank_loans WHERE user_id = ? AND status = 'active'", (user_id,)
    ).fetchone()
    conn.close()
    return row


def request_loan(user_id: int, amount: int, fee_percent: int, installments: int):
    """
    درخواست وام جدید. کارمزد رو به مبلغ کل اضافه میکنه و تقسیم بر اقساط میکنه.
    مبلغ وام مستقیم به کیف پول (meow_points) کاربر واریز میشه.
    خروجی: (success, message, loan_row)
    """
    existing = get_active_loan(user_id)
    if existing:
        return False, "شما همین الان یک وام فعال دارید", None

    fee = int(amount * fee_percent / 100)
    total_amount = amount + fee
    installment_amount = total_amount // installments
    # باقیمانده تقسیم رو به آخرین قسط اضافه میکنیم تا جمع دقیق بمونه
    remainder = total_amount - (installment_amount * installments)

    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO bank_loans
           (user_id, total_amount, remaining_amount, installment_amount,
            installments_total, installments_paid, status, last_payment_time)
           VALUES (?, ?, ?, ?, ?, 0, 'active', ?)""",
        (user_id, total_amount, total_amount, installment_amount, installments, int(time.time())),
    )
    loan_id = cur.lastrowid
    conn.execute(
        "UPDATE users SET meow_points = meow_points + ? WHERE user_id = ?",
        (amount, user_id),
    )
    conn.commit()

    loan = conn.execute("SELECT * FROM bank_loans WHERE id = ?", (loan_id,)).fetchone()
    conn.close()

    return True, f"وام {amount:,} با کارمزد {fee:,} تایید شد", loan


def pay_loan_installment(user_id: int, interval_seconds: int):
    """
    اگه قسط سررسید شده باشه، به‌صورت خودکار از کیف پول کاربر کسر میکنه.
    این تابع باید هر بار که کاربر تعامل می‌کنه (مثلاً موقع باز کردن بانک) صدا زده بشه.
    خروجی: (paid: bool, amount_deducted: int, message: str)
    """
    loan = get_active_loan(user_id)
    if not loan:
        return False, 0, ""

    now = int(time.time())
    elapsed = now - loan["last_payment_time"]

    if elapsed < interval_seconds:
        return False, 0, ""

    from database.models import get_user, add_meow_points

    user = get_user(user_id)
    installment = min(loan["installment_amount"], loan["remaining_amount"])

    conn = get_connection()

    if user["meow_points"] < installment:
        # کاربر موجودی کافی نداره - وام معوق میشه (فعلاً فقط لاگ میکنیم، جریمه‌ی سخت‌گیرانه نداریم)
        conn.close()
        return False, 0, "موجودی کافی برای پرداخت قسط وام نداری! لطفاً شارژ کن."

    add_meow_points(user_id, -installment)

    new_remaining = loan["remaining_amount"] - installment
    new_paid_count = loan["installments_paid"] + 1
    new_status = "paid" if new_remaining <= 0 else "active"

    conn.execute(
        """UPDATE bank_loans
           SET remaining_amount = ?, installments_paid = ?, status = ?, last_payment_time = ?
           WHERE id = ?""",
        (max(0, new_remaining), new_paid_count, new_status, now, loan["id"]),
    )
    conn.commit()
    conn.close()

    return True, installment, f"قسط وام ({installment:,}) به‌صورت خودکار کسر شد"

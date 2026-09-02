#!/usr/bin/env python3
# test_bot.py
# اسکریپت تست خودکار کل منطق ربات - بدون نیاز به تلگرام واقعی
# استفاده: python3 test_bot.py
#
# این اسکریپت یه دیتابیس تست جداگانه و موقت می‌سازه (jojo_test.db) تا با
# دیتابیس اصلی (jojo_bot.db) که کاربرای واقعی توشن، هیچ تداخلی نداشته باشه.
# در پایان، دیتابیس تست رو پاک می‌کنه.

import os
import sys
import time

# قبل از هر ایمپورت دیگه، مسیر دیتابیس رو به یه فایل تستی موقت عوض می‌کنیم
TEST_DB_PATH = "jojo_test.db"
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)

import config
config.DB_PATH = TEST_DB_PATH  # قبل از import های database اعمال بشه

from database.db import init_db, get_connection
from database import models
from database import bank_models
from utils import leveling

PASS = "✅"
FAIL = "❌"
results = []  # (نام تست, موفق؟, توضیح)


def check(name: str, condition: bool, detail: str = ""):
    icon = PASS if condition else FAIL
    results.append((name, condition, detail))
    print(f"{icon} {name}" + (f"  — {detail}" if detail and not condition else ""))


def run_tests():
    print("=" * 50)
    print("شروع تست کامل ربات جوجو")
    print("=" * 50)

    init_db()

    TEST_USER = 999001
    TEST_USER_2 = 999002
    OWNER_TEST = config.OWNER_ID  # از config واقعی میخونیم که owner تست هم منطقی باشه

    # ---------------- ۱. ساخت کاربر ----------------
    print("\n--- ساخت کاربر ---")
    created = models.create_user_if_not_exists(TEST_USER, "test_user")
    check("ساخت کاربر جدید", created is True)

    created_again = models.create_user_if_not_exists(TEST_USER, "test_user")
    check("جلوگیری از ساخت تکراری کاربر", created_again is False)

    user = models.get_user(TEST_USER)
    check("خواندن اطلاعات کاربر", user is not None)
    check("نام پیش‌فرض جوجو صحیح است", user["pet_name"] == config.DEFAULT_PET_NAME, f"مقدار: {user['pet_name']}")
    check("سطح اولیه ۱ است", user["level"] == 1, f"مقدار: {user['level']}")
    check("موجودی اولیه ۰ است", user["meow_points"] == 0, f"مقدار: {user['meow_points']}")

    # ---------------- ۲. ستون‌های جدید (migration) ----------------
    print("\n--- بررسی migration ستون‌های جدید ---")
    try:
        is_jailed_value = user["is_jailed"]
        check("ستون is_jailed در جدول users وجود دارد", True)
        check("مقدار پیش‌فرض is_jailed برابر ۰ است", is_jailed_value == 0, f"مقدار: {is_jailed_value}")
    except (IndexError, KeyError):
        check("ستون is_jailed در جدول users وجود دارد", False, "ستون پیدا نشد - migration کار نکرده")

    # ---------------- ۳. جیک کردن و پاداش ----------------
    print("\n--- جیک کردن و پاداش ---")
    reward = leveling.perform_meow(user["level"])
    check("پاداش جیک کردن عدد مثبت است", reward > 0, f"مقدار: {reward}")

    # تست اینکه پاداش حتی وقتی موجودی از ظرفیت قدیمی بیشتره هم کامل داده میشه
    # (رفع باگ قبلی: پاداش صفر میشد وقتی موجودی به سقف capacity می‌رسید)
    models.add_meow_points(TEST_USER, config.BASE_CAPACITY * 5)  # خیلی بیشتر از ظرفیت پایه
    balance_before_overflow = models.get_user(TEST_USER)["meow_points"]
    reward_overflow = leveling.perform_meow(1)
    models.add_meow_points(TEST_USER, reward_overflow)
    balance_after_overflow = models.get_user(TEST_USER)["meow_points"]
    check(
        "پاداش با موجودی بالای ظرفیت قدیمی هم کامل اعمال می‌شود",
        balance_after_overflow == balance_before_overflow + reward_overflow and reward_overflow > 0,
        f"قبل: {balance_before_overflow}, بعد: {balance_after_overflow}, پاداش: {reward_overflow}",
    )

    balance_before_second_meow = models.get_user(TEST_USER)["meow_points"]
    models.add_meow_points(TEST_USER, reward)
    models.add_exp(TEST_USER, 1)
    models.set_last_meow_time(TEST_USER, int(time.time()))

    user = models.get_user(TEST_USER)
    check(
        "موجودی بعد از جیک افزایش یافت",
        user["meow_points"] == balance_before_second_meow + reward,
        f"مقدار: {user['meow_points']}",
    )
    check("تجربه بعد از جیک افزایش یافت", user["exp"] == 1, f"مقدار: {user['exp']}")

    cooldown = leveling.get_cooldown_seconds(user["level"])
    check("کول‌داون عدد مثبت است", cooldown > 0, f"مقدار: {cooldown}")

    # ---------------- ۴. سیستم سطح ----------------
    print("\n--- سیستم سطح ---")
    needed_lvl2 = leveling.get_exp_required_for_level(2)
    check("نیاز سطح ۲ بیشتر از صفر است", needed_lvl2 > 0, f"مقدار: {needed_lvl2}")

    new_level, leveled_up = leveling.check_level_up(1, needed_lvl2)
    check("ارتقای سطح با exp کافی رخ می‌دهد", leveled_up is True and new_level == 2)

    new_level_no, leveled_up_no = leveling.check_level_up(1, 0)
    check("عدم ارتقای سطح بدون exp کافی", leveled_up_no is False and new_level_no == 1)

    rank_capacity = leveling.get_capacity_for_rank(1)
    check("ظرفیت رنک ۱ برابر پایه است", rank_capacity == config.BASE_CAPACITY, f"مقدار: {rank_capacity}")

    # ---------------- ۵. زندان و بن ----------------
    print("\n--- زندان و بن ---")
    models.set_jailed(TEST_USER, True)
    user = models.get_user(TEST_USER)
    check("زندانی کردن کاربر کار می‌کند", user["is_jailed"] == 1)

    models.set_jailed(TEST_USER, False)
    user = models.get_user(TEST_USER)
    check("آزاد کردن کاربر از زندان کار می‌کند", user["is_jailed"] == 0)

    models.set_banned(TEST_USER, True)
    user = models.get_user(TEST_USER)
    check("بن کردن کاربر کار می‌کند", user["is_banned"] == 1)

    models.set_banned(TEST_USER, False)
    user = models.get_user(TEST_USER)
    check("آنبن کردن کاربر کار می‌کند", user["is_banned"] == 0)

    # ---------------- ۶. ویرایش سطح/موجودی (باگ قبلی) ----------------
    print("\n--- ویرایش سطح و موجودی (رفع باگ قبلی) ---")
    new_rank = (10 - 1) // 5 + 1
    new_cap = leveling.get_capacity_for_rank(new_rank)
    models.set_level(TEST_USER, 10, new_cap, new_rank)
    user = models.get_user(TEST_USER)
    check("ویرایش دستی سطح کاربر کار می‌کند", user["level"] == 10, f"مقدار: {user['level']}")

    old_balance = user["meow_points"]
    target_balance = 5000
    diff = target_balance - old_balance
    models.add_meow_points(TEST_USER, diff)
    user = models.get_user(TEST_USER)
    check("ویرایش دستی موجودی کاربر کار می‌کند", user["meow_points"] == target_balance, f"مقدار: {user['meow_points']}")

    # ---------------- ۷. تغییر نام ----------------
    print("\n--- تغییر نام جوجو ---")
    models.update_pet_name(TEST_USER, "جیکو")
    user = models.get_user(TEST_USER)
    check("تغییر نام جوجو کار می‌کند", user["pet_name"] == "جیکو", f"مقدار: {user['pet_name']}")

    # ---------------- ۸. بانک ----------------
    print("\n--- بانک ---")
    card_number = bank_models.open_bank_account(TEST_USER)
    check("افتتاح حساب بانکی کار می‌کند", card_number is not None and len(card_number) == 12)

    account = bank_models.get_bank_account(TEST_USER)
    check("خواندن حساب بانکی کار می‌کند", account is not None)
    check("موجودی اولیه بانک صفر است", account["balance"] == 0)

    balance_before = models.get_user(TEST_USER)["meow_points"]
    bank_models.deposit_to_bank(TEST_USER, 1000)
    account = bank_models.get_bank_account(TEST_USER)
    user = models.get_user(TEST_USER)
    check("واریز به بانک - موجودی بانک افزایش یافت", account["balance"] == 1000, f"مقدار: {account['balance']}")
    check("واریز به بانک - کیف پول کاهش یافت", user["meow_points"] == balance_before - 1000)

    bank_models.withdraw_from_bank(TEST_USER, 400)
    account = bank_models.get_bank_account(TEST_USER)
    check("برداشت از بانک کار می‌کند", account["balance"] == 600, f"مقدار: {account['balance']}")

    fee = bank_models.calculate_transfer_fee(1000)
    check("محاسبه کارمزد انتقال منطقی است", fee > 0, f"مقدار: {fee}")

    # تست انتقال کارت به کارت بین دو کاربر
    models.create_user_if_not_exists(TEST_USER_2, "test_user_2")
    card_2 = bank_models.open_bank_account(TEST_USER_2)
    bank_models.deposit_to_bank(TEST_USER_2, 0)  # فقط برای اطمینان از وجود حساب فعال

    success, msg = bank_models.card_to_card_transfer(TEST_USER, card_2, 100)
    check("انتقال کارت به کارت موفق است", success is True, msg)

    account_2 = bank_models.get_bank_account(TEST_USER_2)
    check("مقصد انتقال مبلغ را دریافت کرد", account_2["balance"] == 100, f"مقدار: {account_2['balance']}")

    # ---------------- ۹. مارکت ----------------
    print("\n--- مارکت ---")
    conn = get_connection()
    conn.execute(
        """INSERT INTO market_items (name, price, item_type, description)
           VALUES ('آیتم تستی', 50, 'test', 'برای تست')"""
    )
    conn.commit()
    item = conn.execute("SELECT * FROM market_items WHERE name = 'آیتم تستی'").fetchone()
    conn.close()
    check("افزودن آیتم به مارکت کار می‌کند", item is not None and item["price"] == 50)

    # ---------------- ۱۰. لیدربرد ----------------
    print("\n--- لیدربرد ---")
    lb = models.get_leaderboard("meow_points", limit=5)
    check("لیدربرد پوینت خروجی می‌دهد", len(lb) >= 1, f"تعداد: {len(lb)}")

    lb_level = models.get_leaderboard("level", limit=5)
    check("لیدربرد سطح خروجی می‌دهد", len(lb_level) >= 1, f"تعداد: {len(lb_level)}")

    # ---------------- ۱۱. مدیریت ادمین پویا ----------------
    print("\n--- مدیریت ادمین (افزودن/حذف) ---")
    FAKE_ADMIN = 999003
    check("کاربر ابتدا ادمین پویا نیست", models.is_dynamic_admin(FAKE_ADMIN) is False)

    models.add_admin(FAKE_ADMIN, OWNER_TEST)
    check("افزودن ادمین پویا کار می‌کند", models.is_dynamic_admin(FAKE_ADMIN) is True)

    admins_list = models.get_all_dynamic_admins()
    check("لیست ادمین‌های پویا شامل کاربر جدید است", any(a["user_id"] == FAKE_ADMIN for a in admins_list))

    models.remove_admin(FAKE_ADMIN)
    check("حذف ادمین پویا کار می‌کند", models.is_dynamic_admin(FAKE_ADMIN) is False)

    # ---------------- ۱۲. آمار کلی ----------------
    print("\n--- آمار کلی ---")
    stats = models.get_total_stats()
    check("آمار کلی تعداد کاربران را برمی‌گرداند", stats["total_users"] >= 2, f"مقدار: {stats['total_users']}")

    # ---------------- ۱۳. فرمت زمان ----------------
    print("\n--- توابع کمکی ---")
    formatted = leveling.format_time(125)
    check("فرمت زمان mm:ss درست است", formatted == "2:05", f"مقدار: {formatted}")

    # ---------------- خلاصه نهایی ----------------
    print("\n" + "=" * 50)
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = total - passed

    print(f"نتیجه نهایی: {passed}/{total} تست موفق")
    if failed > 0:
        print(f"\n{FAIL} تست‌های ناموفق:")
        for name, ok, detail in results:
            if not ok:
                print(f"  - {name}" + (f" ({detail})" if detail else ""))
    print("=" * 50)

    # پاکسازی دیتابیس تست
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

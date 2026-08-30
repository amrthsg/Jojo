# ربات جوجو 🐾

ربات سرگرمی تلگرام مشابه میویی، با aiogram 3 روی پایتون.

## نصب روی VPS

```bash
cd /root
git clone <repo> jojo_bot   # یا فایل‌ها رو مستقیم آپلود کن
cd jojo_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt --break-system-packages
```

## تنظیمات

فایل `config.py` رو باز کن و این‌ها رو عوض کن:

- `BOT_TOKEN` = توکن ربات از BotFather
- `ADMIN_IDS` = لیست آیدی عددی ادمین‌ها

## اجرا (تست دستی)

```bash
python3 bot.py
```

## اجرا به‌صورت سرویس دائمی (systemd)

فایل `/etc/systemd/system/jojo_bot.service` بساز:

```ini
[Unit]
Description=Jojo Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/jojo_bot
ExecStart=/root/jojo_bot/venv/bin/python3 bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

بعد:

```bash
systemctl daemon-reload
systemctl enable jojo_bot
systemctl start jojo_bot
systemctl status jojo_bot
```

## ساختار پروژه

```
jojo_bot/
├── bot.py                    # نقطه ورود
├── config.py                  # تنظیمات (توکن، ادمین، فرمول‌ها)
├── database/
│   ├── db.py                   # اتصال و ساخت جداول
│   ├── models.py                # CRUD کاربران
│   └── bank_models.py            # منطق بانک
├── handlers/
│   ├── start.py                  # /start
│   ├── meow.py                    # میو کردن، سطح، پروفایل
│   ├── bank.py                     # بانک
│   ├── market.py                    # مارکت
│   ├── leaderboard.py                # لیدربرد
│   ├── admin.py                       # پنل ادمین
│   └── games/
│       └── table_games.py              # بسکتبال/بولینگ/دارت/فوتبال
├── keyboards/
│   └── main_kb.py                       # کیبوردها
└── utils/
    └── leveling.py                        # فرمول سطح و کول‌داون
```

## نکات مهم برای توسعه بیشتر

1. **فرمول‌های سطح/پاداش** تو `utils/leveling.py` تقریبی و بر اساس مشاهداته —
   با تست واقعی می‌تونی عدد‌ها رو فاین‌تیون کنی.

2. **دیتابیس SQLite** برای شروع خوبه؛ اگه کاربرات زیاد شدن (بالای چند هزار فعال)
   بهتره بری سراغ PostgreSQL.

3. **بازی‌های میزی** فعلاً فقط برای ۲ نفر پیاده‌سازی شده. برای فوتبال هم از
   ایموجی ⚽ تلگرام استفاده شده که مقدار ۱ تا ۵ برمیگردونه (۵ = گل کامل).

4. **امنیت پنل ادمین**: چک `is_admin()` فقط بر اساس `ADMIN_IDS` تو config.py هست.
   اگه میخوای پویا (از دیتابیس) باشه، باید یه جدول admins هم اضافه کنی.

5. **فازهای بعدی** که هنوز پیاده نشدن: کارخونه، ماهیگیری، کازینو، شهر پیشی،
   قاچاق، قرعه‌کشی، یخچال. این‌ها رو میتونیم به همین ساختار اضافه کنیم.

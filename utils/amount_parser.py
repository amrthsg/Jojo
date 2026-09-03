# utils/amount_parser.py
# پارس کردن مقادیر عددی با پسوندهای رایج فارسی/انگلیسی
# پشتیبانی از فرمت‌هایی مثل: 500, 5k, 5m, 5kk, 1.5k

import re

# پسوندهای رایج و ضریب هرکدوم
_SUFFIX_MULTIPLIERS = {
    "k": 1_000,
    "کی": 1_000,
    "کا": 1_000,
    "کک": 1_000_000,   # کک = هزار هزار = میلیون (اصطلاح رایج تو بازی‌های ایرانی)
    "kk": 1_000_000,
    "m": 1_000_000,
    "میل": 1_000_000,
    "میلیون": 1_000_000,
}

_AMOUNT_PATTERN = re.compile(
    r"^(\d+(?:\.\d+)?)\s*(کک|کی|کا|میلیون|میل|kk|k|m)?$",
    re.IGNORECASE,
)


def parse_amount(text: str) -> int | None:
    """
    یک رشته مثل '500' یا '5k' یا '1.5m' رو به عدد صحیح تبدیل میکنه.
    اگه فرمت نامعتبر بود، None برمیگردونه.
    """
    text = text.strip()
    match = _AMOUNT_PATTERN.match(text)
    if not match:
        return None

    number_str, suffix = match.groups()
    number = float(number_str)

    if suffix:
        multiplier = _SUFFIX_MULTIPLIERS.get(suffix.lower())
        if multiplier is None:
            return None
        number *= multiplier

    return int(number)

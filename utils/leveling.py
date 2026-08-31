# utils/leveling.py
# محاسبات مربوط به سطح، کول‌داون جیک و پاداش

import random
from config import (
    MEOW_COOLDOWN_BASE,
    MEOW_COOLDOWN_MIN,
    MEOW_COOLDOWN_STEP_LEVELS,
    MEOW_COOLDOWN_STEP_SECONDS,
    MAX_LEVEL,
    BASE_CAPACITY,
    CAPACITY_GROWTH_PER_RANK,
)


def get_cooldown_seconds(level: int) -> int:
    """
    کول‌داون بر اساس سطح؛ هر چند سطح چند ثانیه کمتر میشه،
    ولی هیچوقت از حداقل تعیین‌شده کمتر نمیشه.
    """
    steps = level // MEOW_COOLDOWN_STEP_LEVELS
    cooldown = MEOW_COOLDOWN_BASE - steps * MEOW_COOLDOWN_STEP_SECONDS
    return max(cooldown, MEOW_COOLDOWN_MIN)


def get_exp_required_for_level(level: int) -> int:
    """
    تعداد جیک تجمعی موردنیاز برای رسیدن به یک سطح.
    فرمول تقریبی بر اساس داده‌های مشاهده‌شده (رشد تصاعدی ملایم).
    سطح 1 = 0, سطح 2 = 5, سطح 4 = 40, سطح 7 = 175, سطح 10 = 475 ...
    """
    if level <= 1:
        return 0
    # فرمول تقریبی: رشد درجه دو با ضریب افزایشی
    return int(5 * (level - 1) ** 2.15)


def get_reward_range_for_level(level: int) -> tuple[int, int]:
    """
    رنج پاداش جیک کردن برای یک سطح مشخص (min, max).
    بر اساس مشاهدات: سطح 1: 5-15, سطح 25: 500-925, سطح 50: 1500-2500
    """
    base_min = 5 + int(level * 30)
    base_max = int(base_min * 1.7) + 10
    return base_min, base_max


def get_level_up_reward(level: int) -> int:
    """پاداش یکجا موقع ارتقای سطح"""
    exp_needed = get_exp_required_for_level(level + 1) - get_exp_required_for_level(level)
    return int(exp_needed * 8)  # ضریب تجربی بر اساس داده‌ها


def get_capacity_for_rank(rank: int) -> int:
    """ظرفیت شکم/جیب بر اساس مقام (rank). هر ۵ سطح یک رنک بالاتر"""
    return int(BASE_CAPACITY * (CAPACITY_GROWTH_PER_RANK ** (rank - 1)))


def check_level_up(current_level: int, current_exp: int):
    """
    چک می‌کنه آیا کاربر با exp فعلی باید سطح بره یا نه.
    خروجی: (new_level, leveled_up: bool)
    """
    level = current_level
    leveled_up = False
    while level < MAX_LEVEL and current_exp >= get_exp_required_for_level(level + 1):
        level += 1
        leveled_up = True
    return level, leveled_up


def perform_meow(level: int) -> int:
    """یک بار جیک کردن انجام میده و مقدار پوینت دریافتی رو برمیگردونه"""
    min_r, max_r = get_reward_range_for_level(level)
    return random.randint(min_r, max_r)


def format_time(seconds: int) -> str:
    """تبدیل ثانیه به فرمت mm:ss برای نمایش تو پیام"""
    seconds = max(0, int(seconds))
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"

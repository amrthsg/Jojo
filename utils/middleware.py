# utils/middleware.py
# میدلور ساده برای به‌روز نگه‌داشتن display_name کاربر در هر تعامل

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

from database.models import get_user, update_display_name


class DisplayNameMiddleware(BaseMiddleware):
    """
    هر بار کاربری که از قبل تو دیتابیس هست پیامی میفرسته، اگه اسم تلگرامش
    عوض شده باشه (مثلاً اسمشو عوض کرده)، دیتابیس رو به‌روز میکنه.
    این کار سبک و بی‌خطره چون فقط یک UPDATE ساده‌ست و مسدودکننده نیست.
    """

    async def __call__(self, handler, event: TelegramObject, data: dict):
        if isinstance(event, Message) and event.from_user and not event.from_user.is_bot:
            user = get_user(event.from_user.id)
            if user:
                new_display_name = event.from_user.full_name
                new_username = event.from_user.username
                if user["display_name"] != new_display_name or user["username"] != new_username:
                    update_display_name(event.from_user.id, new_display_name, new_username)

        return await handler(event, data)

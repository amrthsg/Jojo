# handlers/games/table_games.py
# منطق بازی‌های میزی: بسکتبال، بولینگ، دارت، فوتبال
# دو نفره، شرط‌بندی پوینت، برنده کل میز رو میبره، مساوی = برگشت پول

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.models import get_user, add_meow_points
from database.db import get_connection
from keyboards.main_kb import games_menu_kb
from config import GAME_TYPES, GAMES_MIN_LEVEL, GAMES_TABLE_MIN_LEVEL

router = Router()

GAME_NAMES_FA = {
    "basketball": "بسکتبال",
    "bowling": "بولینگ",
    "darts": "دارت",
    "football": "فوتبال",
}


class GameStates(StatesGroup):
    waiting_bet_amount = State()


@router.message(F.text == "🎮 بازی‌ها")
async def handle_games_menu(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("اول باید /start بزنی 🐱")
        return

    if user["level"] < GAMES_MIN_LEVEL:
        await message.answer(f"🎮 برای بازی کردن باید حداقل سطح {GAMES_MIN_LEVEL} باشی.")
        return

    await message.answer(
        "🎮 <b>بازی‌های جوجو</b>\n\nیکی از بازی‌ها رو انتخاب کن:",
        reply_markup=games_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("game_"))
async def cb_select_game(callback: CallbackQuery, state: FSMContext):
    game_type = callback.data.replace("game_", "")

    user = get_user(callback.from_user.id)
    if user["level"] < GAMES_TABLE_MIN_LEVEL:
        await callback.answer(
            f"برای ساخت میز بازی باید حداقل سطح {GAMES_TABLE_MIN_LEVEL} باشی", show_alert=True
        )
        return

    await state.update_data(game_type=game_type)
    await callback.message.answer(
        f"{GAME_TYPES[game_type]} چه مقدار {'' } میخوای شرط ببندی؟ (فقط عدد بفرست)"
    )
    await state.set_state(GameStates.waiting_bet_amount)
    await callback.answer()


@router.message(GameStates.waiting_bet_amount)
async def process_bet_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ فقط عدد بفرست.")
        return

    amount = int(message.text)
    user = get_user(message.from_user.id)

    if amount <= 0 or amount > user["meow_points"]:
        await message.answer("❌ موجودی کافی نیست.")
        await state.clear()
        return

    data = await state.get_data()
    game_type = data["game_type"]

    # کسر پول از سازنده میز و رزرو اون تا وقتی بازی تموم بشه
    add_meow_points(message.from_user.id, -amount)

    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO game_tables (chat_id, game_type, creator_id, bet_amount, status)
           VALUES (?, ?, ?, ?, 'waiting')""",
        (message.chat.id, game_type, message.from_user.id, amount),
    )
    table_id = cur.lastrowid
    conn.execute(
        "INSERT INTO game_players (table_id, user_id) VALUES (?, ?)",
        (table_id, message.from_user.id),
    )
    conn.commit()
    conn.close()

    await message.answer(
        f"🎲 میز {GAME_NAMES_FA[game_type]} با شرط {amount:,} ساخته شد!\n"
        f"برای پیوستن بنویس: <code>پیوستن {table_id}</code>",
        parse_mode="HTML",
    )
    await state.clear()


@router.message(F.text.startswith("پیوستن "))
async def handle_join_table(message: Message):
    try:
        table_id = int(message.text.replace("پیوستن ", "").strip())
    except ValueError:
        await message.answer("❌ شماره میز نامعتبره.")
        return

    conn = get_connection()
    table = conn.execute(
        "SELECT * FROM game_tables WHERE table_id = ? AND status = 'waiting'",
        (table_id,),
    ).fetchone()

    if not table:
        conn.close()
        await message.answer("❌ این میز پیدا نشد یا قبلاً شروع شده.")
        return

    if table["creator_id"] == message.from_user.id:
        conn.close()
        await message.answer("❌ نمیتونی به میز خودت بپیوندی.")
        return

    user = get_user(message.from_user.id)
    if user["meow_points"] < table["bet_amount"]:
        conn.close()
        await message.answer("❌ موجودی کافی برای این شرط نداری.")
        return

    add_meow_points(message.from_user.id, -table["bet_amount"])

    conn.execute(
        "INSERT INTO game_players (table_id, user_id) VALUES (?, ?)",
        (table_id, message.from_user.id),
    )
    conn.execute(
        "UPDATE game_tables SET status = 'active' WHERE table_id = ?",
        (table_id,),
    )
    conn.commit()
    conn.close()

    game_emoji = GAME_TYPES[table["game_type"]]
    await message.answer(
        f"✅ بازی شروع شد! هر دو نفر باید {game_emoji} رو بفرستن تا امتیاز ثبت بشه."
    )


@router.message(F.dice)
async def handle_dice_roll(message: Message):
    """
    وقتی کاربر یک دایس (🏀🎳🎯⚽) میفرسته، اگه تو یه میز فعال باشه امتیازش ثبت میشه.
    """
    emoji = message.dice.emoji
    game_type = None
    for key, val in GAME_TYPES.items():
        if val == emoji:
            game_type = key
            break

    if not game_type:
        return

    conn = get_connection()
    table = conn.execute(
        """SELECT * FROM game_tables
           WHERE chat_id = ? AND game_type = ? AND status = 'active'
           ORDER BY table_id DESC LIMIT 1""",
        (message.chat.id, game_type),
    ).fetchone()

    if not table:
        conn.close()
        return

    player = conn.execute(
        "SELECT * FROM game_players WHERE table_id = ? AND user_id = ? AND score = 0",
        (table["table_id"], message.from_user.id),
    ).fetchone()

    if not player:
        conn.close()
        return

    conn.execute(
        "UPDATE game_players SET score = ? WHERE id = ?",
        (message.dice.value, player["id"]),
    )
    conn.commit()

    # چک اینکه هر دو بازیکن امتیازشون رو ثبت کردن
    players = conn.execute(
        "SELECT * FROM game_players WHERE table_id = ?", (table["table_id"],)
    ).fetchall()

    if len(players) == 2 and all(p["score"] > 0 for p in players):
        p1, p2 = players[0], players[1]
        total_pot = table["bet_amount"] * 2

        if p1["score"] > p2["score"]:
            winner_id = p1["user_id"]
        elif p2["score"] > p1["score"]:
            winner_id = p2["user_id"]
        else:
            winner_id = None  # مساوی

        if winner_id:
            add_meow_points(winner_id, total_pot)
            result_text = f"🏆 برنده: {winner_id} با امتیاز بیشتر! جایزه: {total_pot:,}"
        else:
            # مساوی - برگشت پول به هر دو نفر
            add_meow_points(p1["user_id"], table["bet_amount"])
            add_meow_points(p2["user_id"], table["bet_amount"])
            result_text = "🤝 مساوی شد (WP)! پول‌ها برگشت داده شد."

        conn.execute(
            "UPDATE game_tables SET status = 'finished' WHERE table_id = ?",
            (table["table_id"],),
        )
        conn.commit()
        conn.close()

        await message.answer(result_text)
        return

    conn.close()

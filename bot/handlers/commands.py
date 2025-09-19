from aiogram import types, Router, F
from aiogram.filters import Command
from config.logging_config import get_logger

from db.db_setup import add_user
from bot.keyboards.user_keyboards import get_main_menu_keyboard

logger = get_logger(__name__)
router = Router()



@router.message(Command("start"))
async def start_command(message: types.Message) -> None:
    """Handle /start command."""
    try:
        telegram_id = message.from_user.id
        
        logger.info(f"User {telegram_id} started the bot")

        welcome_text = (
            "👋 Добро пожаловать в <b>KrisaVPN</b> bot!"
        )

        user = await add_user(telegram_id=telegram_id)
        keyboard = get_main_menu_keyboard(user.eligible_for_trial)
        await message.answer(welcome_text, reply_markup=keyboard, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error handling /start command from user {message.from_user.id}: {e}")
        await message.answer("Извините, что-то пошло не так.")







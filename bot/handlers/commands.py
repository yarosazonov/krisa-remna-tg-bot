from aiogram import types, Router, F
from aiogram.filters import Command
from config.logging_config import get_logger

from db.db_setup import add_user, get_user
from bot.keyboards.user_keyboards import get_main_menu_keyboard
from config.settings import get_settings
from bot.services.remnawave_service import RemnawaveService
from bot.middlewares.id_check_middleware import UserIDMiddleware

logger = get_logger(__name__)
router = Router()
# Register the middlewares
router.message.middleware(UserIDMiddleware())



@router.message(Command("start"))
async def start_command(message: types.Message, telegram_id: int) -> None:
    """Handle /start command."""
    try:
        logger.info(f"User {telegram_id} started the bot")

        welcome_text = (
            "👋 Добро пожаловать в <b>КрысаВПН</b> bot 2.0!\n"
        )
        user = await get_user(telegram_id=telegram_id)
        if user:
            logger.info(f"User with id: {telegram_id} is found in the database")
            keyboard = get_main_menu_keyboard(user.eligible_for_trial)
        else:
            logger.info(f"User with id: {telegram_id} isn't in the database")
            new_user = await add_user(telegram_id=telegram_id)
            keyboard = get_main_menu_keyboard(new_user.eligible_for_trial)
        await message.answer(welcome_text, reply_markup=keyboard, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error handling /start command from user {message.from_user.id}: {e}")
        await message.answer("Извините, что-то пошло не так.")



@router.message(Command("sync"))
async def sync_command(message: types.Message, telegram_id: int, remnawave_service: RemnawaveService) -> None:
    logger.info(f"User {telegram_id} requested /sync")
    settings = get_settings()
    admin_id = settings.ADMIN_ID

    if telegram_id != admin_id:
        await message.reply("❌ Ты не админ, тебе нельзя!")
        return

    total, with_ids = await remnawave_service.sync_with_panel()
    await message.reply(f"✅ Синхронизация с панелью прошла успешно. Всего найдено юзеров: {total}, из них имеют тг id: {with_ids}")



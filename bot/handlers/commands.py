from aiogram import types, Router, F
from aiogram.filters import Command
from config.logging_config import get_logger

from db.db_setup import add_user, get_user
from bot.keyboards.user_keyboards import get_main_menu_keyboard
from config.settings import get_settings
from bot.services.remnawave_service import RemnawaveService

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
async def start_command(message: types.Message) -> None:
    tg_id = message.from_user.id
    logger.info(f"User {tg_id} requested /sync")
    settings = get_settings()
    admin_id = settings.ADMIN_ID

    if tg_id != admin_id:
        await message.reply("❌ Ты не админ, тебе нельзя!")
        return
    
    remnawave_service = RemnawaveService(
            api_url=settings.REMNAWAVE_API_URL,
            api_token=settings.REMNAWAVE_API_TOKEN
        )
    
    total, with_ids = await remnawave_service.sync_with_panel()
    await message.reply(f"✅ Синхронизация с панелью прошла успешно. Всего найдено юзеров: {total}, из них имеют тг id: {with_ids}")



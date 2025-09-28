from aiogram import types, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import FSInputFile

from config.logging_config import get_logger
from db.db_setup import add_user, get_user, update_user
from bot.keyboards.user_keyboards import get_main_menu_keyboard
from config.settings import get_settings
from bot.services.remnawave_service import RemnawaveService
from bot.middlewares.id_check_middleware import UserIDMiddleware



logger = get_logger(__name__)
router = Router()
# Register the middlewares
router.message.middleware(UserIDMiddleware())

# Insert welcome text, also used in main_menu callback
WELCOME_TEXT = (
    "👋 Добро пожаловать в <b>КрысаВПН</b> bot 2.0!\n\n"
    "У нас:\n\n"
    "💡 <b>Идея:</b> интернет должен быть свободным!\n"
    "⚡ <b>Высокая скорость:</b> наши сервера не забиты под завязку.\n"
    "💰 <b>Низкие цены:</b> наш приоритет — доступность.\n"
    "🤝 <b>Возможность заработать:</b> крутая реферальная программа!"
)



# =================
# Handle the /start
# =================
@router.message(CommandStart())
async def start_command(message: types.Message, command: CommandObject, telegram_id: int) -> None:
    """
    Handle /start command, both plain and via deep link.
    """
    try:
        logger.info(f"User {telegram_id} started the bot")
        try:
            telegram_username = message.from_user.username
        except Exception as e:
            logger.warning(f"No username for user with id: {telegram_id}")
            telegram_username = None

        # Check for deep link referral ID
        referrer_id = int(command.args) if command.args and command.args.isdigit() else None
        if referrer_id:
            logger.info(f"User {telegram_id} came via referral link from {referrer_id}")

        # Fetch or create user
        user = await get_user(telegram_id=telegram_id)
        if user:
            logger.info(f"User with id: {telegram_id} is found in the database")
            if telegram_username and user.telegram_username != telegram_username:
                logger.warning(f"Updating username for user {telegram_id} to {telegram_username}")
                await update_user(telegram_id=telegram_id, telegram_username=telegram_username)
        else:
            logger.info(f"User with id: {telegram_id} isn't in the database")
            user = await add_user(
                telegram_id=telegram_id, 
                referrer_id=referrer_id, 
                telegram_username=telegram_username
            )

        keyboard = get_main_menu_keyboard(user.eligible_for_trial)
        
        await message.answer(
            text=WELCOME_TEXT, 
            reply_markup=keyboard, 
            parse_mode='HTML'
            )

    except Exception as e:
        logger.exception(f"Error handling /start command from user {telegram_id}: {e}")
        await message.answer("Извините, что-то пошло не так.")



# ================
# Handle the /sync
# ================
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



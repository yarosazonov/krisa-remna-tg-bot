import asyncio
from aiogram import types, Router
from aiogram.filters import Command
from config.logging_config import get_logger
from config.settings import get_settings
from bot.services.remnawave_service import RemnawaveService

logger = get_logger(__name__)
router = Router()



@router.message(Command("start"))
async def start_command(message: types.Message) -> None:
    """Handle /start command."""
    try:
        logger.info(f"User {message.from_user.id} started the bot")

        welcome_text = (
            "👋 Добро пожаловать в **KrisaVPN** bot!"
        )

        await message.answer(welcome_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error handling /start command from user {message.from_user.id}: {e}")
        await message.answer("Извините, что-то пошло не так.")



@router.message(Command("help"))
async def help_command(message: types.Message) -> None:
    """Handle /help command."""
    try:
        logger.info(f"User {message.from_user.id} requested help")

        help_text = (
            "🤖 Команды бота:\n\n"
            "/start - Главное меню бота\n"
            "/status - Проверить статус подписки\n"
        )

        await message.answer(help_text, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error handling /help command from user {message.from_user.id}: {e}")
        await message.answer("Извините, что-то пошло не так.")



@router.message(Command("status"))
async def status_command(message: types.Message) -> None:
    """Handle /status command to check subscription status."""
    try:
        telegram_id = message.from_user.id
        logger.info(f"User {telegram_id} requested subscription status")

        await message.answer("🔍 Проверяю статус вашей подписки...")

        settings = get_settings()
        remnawave_service = RemnawaveService(
            api_url=settings.REMNAWAVE_API_URL,
            api_token=settings.REMNAWAVE_API_TOKEN
        )

        user_data = await remnawave_service.get_user_by_telegram_id(telegram_id)

        if user_data is None:
            await message.answer(
                "❌ **Подписка не найдена**\n\n"
                "Активная подписка для вашего Telegram аккаунта не найдена.\n"
                "Обратитесь в поддержку, если считаете, что это ошибка."
            )
            return

        status_text = remnawave_service.format_subscription_status(user_data)

        await message.answer(
            f"🔐 <b>Ваша подписка:</b>\n\n{status_text}",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error handling /status command from user {message.from_user.id}: {e}")
        await message.answer(
            "❌ **Ошибка**\n\n"
            "В данный момент невозможно получить статус подписки.\n"
            "Попробуйте позже или обратитесь в поддержку."
        )
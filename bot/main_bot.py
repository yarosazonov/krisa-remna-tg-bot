from aiogram import Bot, Dispatcher
from bot.handlers import commands, callbacks
from bot.services.yookassa_service import YooKassaService
from bot.services.remnawave_service import RemnawaveService
from config.logging_config import get_logger


logger = get_logger(__name__)


async def init_bot(settings):
    """Initialize bot with separated handlers."""
    logger.info("Initializing bot...")

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # Initialize services
    remnawave_service = RemnawaveService(
        api_url=settings.REMNAWAVE_API_URL,
        api_token=settings.REMNAWAVE_API_TOKEN
    )

    yookassa_service = YooKassaService(
        shop_id=settings.YOOKASSA_SHOP_ID,
        secret_key=settings.YOOKASSA_SECRET_KEY,
        configured_return_url=settings.YOOKASSA_RETURN_URL,
        bot_username_for_default_return=None,
        settings_obj=settings
    )



    # Storing service's objects for dependency injection in handlers
    dp["remnawave_service"] = remnawave_service
    dp["yookassa_service"] = yookassa_service



    # Including routers
    dp.include_router(commands.router)
    dp.include_router(callbacks.router)

    logger.info("Bot initialized successfully")
    return bot, dp
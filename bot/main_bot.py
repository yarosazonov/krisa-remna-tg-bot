from aiogram import Bot, Dispatcher

from bot.handlers import commands, callbacks
from bot.services.yookassa_service import YooKassaService
from bot.services.remnawave_service import RemnawaveService
from config.logging_config import get_logger
from bot.middlewares.id_check_middleware import UserIDMiddleware

logger = get_logger(__name__)



async def init_bot(
        settings, 
        remnawave_service: RemnawaveService, 
        yookassa_service: YooKassaService
        ) -> tuple[Bot, Dispatcher]:
    """Initialize bot with separated handlers."""
    logger.info("Initializing bot...")

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # Storing service's objects for dependency injection in handlers
    dp["remnawave_service"] = remnawave_service
    dp["yookassa_service"] = yookassa_service
   


    # Including routers
    dp.include_router(commands.router)
    dp.include_router(callbacks.router)

    logger.info("Bot initialized successfully")
    return bot, dp
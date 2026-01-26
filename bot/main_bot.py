from aiogram import Bot, Dispatcher

from bot.handlers import commands_router, callbacks_router
from bot.services import YooKassaService, RemnawaveService
from config import get_logger
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
    dp.include_router(commands_router)
    dp.include_router(callbacks_router)

    logger.info("Bot initialized successfully")
    return bot, dp
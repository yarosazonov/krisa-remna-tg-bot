from aiogram import Bot, Dispatcher
from bot.handlers import commands
from config.logging_config import get_logger

logger = get_logger(__name__)


async def init_bot(settings):
    """Initialize bot with separated handlers."""
    logger.info("Initializing bot...")

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # Include routers
    dp.include_router(commands.router)

    logger.info("Bot initialized successfully")
    return bot, dp
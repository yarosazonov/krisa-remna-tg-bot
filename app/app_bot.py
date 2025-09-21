import asyncio
from fastapi import FastAPI, Request, HTTPException
from aiogram import types
from contextlib import asynccontextmanager
from bot.main_bot import init_bot
from config.logging_config import get_logger
from bot.handlers.payment import handle_yookassa_update
from bot.services.yookassa_service import YooKassaService
from bot.services.remnawave_service import RemnawaveService

logger = get_logger(__name__)


def create_app(settings):
    """Create FastAPI app with Telegram bot integration."""

    bot = None
    dp = None  

    # Initializing services
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
    # this decorator treats everything before yield as __enter__() and after yeild as __exit__()
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage bot startup and shutdown."""
        nonlocal bot, dp
        try:
            logger.info("Starting bot setup...")
            bot, dp = await init_bot(settings, remnawave_service=remnawave_service, yookassa_service=yookassa_service)
            await bot.set_webhook(settings.WEBHOOK_URL)
            logger.info(f"Webhook set to: {settings.WEBHOOK_URL}")
            yield
        except Exception as e:
            logger.error(f"Error during bot setup: {e}")
            raise
        finally:
            # Checks if bot is truthy or not
            if bot:
                try:
                    logger.info("Cleaning up bot...")
                    await bot.delete_webhook()
                    await bot.session.close()
                    logger.info("Bot cleanup completed")
                except Exception as e:
                    logger.error(f"Error during bot cleanup: {e}")

    # Creation of FastAPI app, the lifespan function defined above is passed inside
    app = FastAPI(lifespan=lifespan)



    # Telegram webhook
    #
    #
    @app.post(settings.WEBHOOK_PATH)
    async def webhook(request: Request):
        """Handle incoming Telegram updates via webhook."""
        try:
            logger.debug("Received webhook request")
            
            # reads the request body and parses it into a Python dictionary
            update_data = await request.json()

            # types.Update() is an aiogram model
            # **update_data unpacks the dictionary into keyword arguments for the Update constructor
            # This converts the raw JSON into a structured Python object with proper attributes like
            # telegram_update.message.text, telegram_update.message.chat.id, etc.
            telegram_update = types.Update(**update_data)

            # Feeding the update to the Dispatcher
            # bot is passed into the method so the Dispatcher can use it to respond
            asyncio.create_task(dp.feed_update(bot, telegram_update))

            # Responce to telegram after processing
            return {"ok": True}

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")



    # Yookassa webhood
    #
    #
    @app.post(settings.YOOKASSA_WEBHOOK_PATH)
    async def yookassa_webhook(request: Request):
        """Handle incoming yookassa payment updates"""
        try:
            logger.debug("Received Yookassa webhood request")
            update_data = await request.json()
            event = update_data.get("event")
            obj = update_data.get("object", {})

            logger.info(f"YooKassa event received: {event}, object: {obj}")
            # Dispatch handling in background
            asyncio.create_task(handle_yookassa_update(event, obj, remnawave_service))

            return {"ok": True}
        except Exception as e:
            logger.error(f"Error processing YooKassa webhook: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    return app

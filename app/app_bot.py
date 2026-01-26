import asyncio
import json
from fastapi import FastAPI, Request, HTTPException, Header
from aiogram import types
from contextlib import asynccontextmanager

from bot.main_bot import init_bot
from config import get_logger
from bot.handlers import handle_yookassa_update
from bot.services import YooKassaService, RemnawaveService, remnawave_webhook_notification

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
    # This decorator treats everything before yeild as __enter__() and after yeild as __exit__()
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage bot startup and shutdown."""
        nonlocal bot, dp
        try:
            logger.info("Starting bot setup...")
            bot, dp = await init_bot(settings, remnawave_service=remnawave_service, yookassa_service=yookassa_service)
            await bot.set_webhook(settings.WEBHOOK_URL, secret_token=settings.WEBHOOK_SECRET)
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
    async def webhook(request: Request, x_telegram_bot_api_secret_token: str = Header()):
        """Handle incoming Telegram updates via webhook."""
        if x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET:
            logger.warning("Unauthorized Telegram webhook request")
            raise HTTPException(status_code=403, detail="Forbidden")
        
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



    # Yookassa webhook
    #
    #
    @app.post(settings.YOOKASSA_WEBHOOK_PATH)
    async def yookassa_webhook(request: Request):
        """Handle incoming yookassa payment updates"""
        nonlocal bot
        try:
            logger.debug("Received Yookassa webhook request")
            update_data = await request.json()
            event = update_data.get("event")
            obj = update_data.get("object", {})

            logger.info(f"YooKassa event received: {event}, object: {obj}")
            
            # Checking the original ip by caddy header
            ip = request.headers.get("X-Forwarded-For")

            # No X-Forwarded-For header, taking the direct ip
            if not ip:
                logger.info("No X-Forwarded-For header, taking the direct ip")
                ip = request.client.host 
                if not yookassa_service.is_ip_valid(ip=ip):
                    raise HTTPException(status_code=401, detail="Ip is not a valid yookassa ip")
                
                # Yookassa payment update handler
                asyncio.create_task(handle_yookassa_update(
                    event=event, 
                    obj=obj, 
                    remnawave_service=remnawave_service,
                    yookassa_service=yookassa_service,
                    bot=bot
                    ))
                return {"ok": True}

            logger.info(f"Found X-Forwarded-For header: {ip}")
            ip = ip.split(",")[0].strip()
            if not yookassa_service.is_ip_valid(ip=ip):
                    raise HTTPException(status_code=401, detail="Ip is not a valid yookassa ip")
            
            # Yookassa payment update handler
            asyncio.create_task(handle_yookassa_update(
                event=event, 
                obj=obj, 
                remnawave_service=remnawave_service, 
                yookassa_service=yookassa_service,
                bot=bot
                ))
            return {"ok": True}
            

            
        except Exception as e:
            logger.error(f"Error processing YooKassa webhook: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
        

        
    # Remnawave webhook
    #
    #
    @app.post(settings.REMNAWAVE_WEBHOOK_PATH)
    async def remnawave_webhook(request: Request):
        nonlocal bot
        body = await request.body()
        signature = request.headers.get("X-Remnawave-Signature")
        
        if not remnawave_service.validate_webhook(body=body, signature=signature, webhook_secret_header=settings.REMNAWAVE_WEBHOOK_SECRET_HEADER):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        payload = json.loads(body)
        event = payload.get("event")
        logger.warning(f"Remna webhook event: {event}")
        if event not in ("user.expires_in_24_hours", "user.expired", "user.limited"):
            return {"status": "ok"}
        user = payload.get("data", {})
        telegram_id = user.get("telegramId")

        if not telegram_id:
            logger.warning(f"No Telegram ID for user {user.get('uuid')}, skipping message.")
            return {"status": "ok"}

        asyncio.create_task(remnawave_webhook_notification(bot=bot, telegram_id=telegram_id, event=event))
        return {"status": "ok"}



    return app



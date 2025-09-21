import asyncio
from fastapi import HTTPException, Request
from datetime import datetime, timezone
from config.logging_config import get_logger
from bot.services.remnawave_service import RemnawaveService
from config.settings import get_settings

logger = get_logger(__name__)



async def handle_yookassa_update(event: str, obj: dict, remnawave_service: RemnawaveService):
    """
    Handles YooKassa payment events.
    """
    settings = get_settings()
    try:
        if event == "payment.succeeded":
            metadata = obj.get("metadata", {})
            tg_id_str = metadata.get("telegram_id")
            subscription_months_str = metadata.get("subscription_months")

            if not tg_id_str or not subscription_months_str:
                logger.error(f"Missing metadata in payment.succeeded event: {metadata}")
                return

            try:
                tg_id = int(tg_id_str)
                subscription_months = int(subscription_months_str)
            except ValueError:
                logger.error(f"Invalid metadata values: {metadata}")
                return

            # Convert months → days (approximate, 30 days per month)
            subscription_days = subscription_months * 30

            # For simplicity, set traffic and squads defaults; modify as needed
            traffic_gb = settings.MONTHLY_TRAFFIC_GB  
            internal_squads = settings.SQUADS  
            tg_tag = metadata.get("user_tag")

            logger.info(f"Processing successful payment for tg_id={tg_id}: +{subscription_days} days")
            # Trigger the payment handling in background
            await remnawave_service.handle_payment(
                tg_id=tg_id,
                tg_tag=tg_tag,
                subscription_days=subscription_days,
                traffic=traffic_gb,
                internal_squads=internal_squads
            )

        elif event == "payment.canceled":
            logger.info(f"Payment canceled: {obj.get('id')}")
            # Optionally, handle cancellations here (refunds, notifications, etc.)

        else:
            logger.warning(f"Unhandled YooKassa event type: {event}")

    except Exception as e:
        logger.error(f"Error handling YooKassa update: {e}")

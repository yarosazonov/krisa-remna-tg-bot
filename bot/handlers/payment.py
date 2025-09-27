import math
from aiogram import Bot

from config.logging_config import get_logger
from bot.services.remnawave_service import RemnawaveService
from config.settings import get_settings
from db.db_setup import get_user, update_user
from bot.services.notification_service import balance_credit_notify
from helpers.helpers import months_to_days

logger = get_logger(__name__)



async def handle_yookassa_update(event: str, obj: dict, remnawave_service: RemnawaveService, bot: Bot):
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

            # Convert months → days 
            subscription_days = months_to_days(subscription_months) 

            # For simplicity, set traffic and squads defaults; modify as needed
            tg_tag = metadata.get("user_tag")

            logger.info(f"Processing successful payment for tg_id={tg_id}: +{subscription_days} days")
            # Trigger the payment handling in background
            await remnawave_service.handle_payment(
                tg_id=tg_id,
                tg_tag=tg_tag,
                subscription_days=subscription_days
            )
            
            # Balance operations
            user = await get_user(telegram_id=tg_id)

            reset_balance = metadata.get("reset_balance")
            if str(reset_balance).lower() == "true":
                logger.warning(f"Balance reset: {reset_balance}. Reseting the balance")
                balance = user.balance
                await update_user(telegram_id=tg_id, balance_increment=-balance)

            # Updating referrers internal balance
            user_referrer_id = user.referrer_id

            if user_referrer_id:
                try:
                    referrer =  await get_user(telegram_id=user_referrer_id)
                    paid_amount = float(obj.get("amount", {}).get("value", 0))
                    paid_amount = int(paid_amount)
                except Exception as e:
                    logger.error(f"Error while getting paid amount to update internal balance: {e}")
                    paid_amount = 0

                ref_percentage = referrer.ref_cashback_percentage / 100
                balance_increment = int(math.floor(paid_amount * ref_percentage))
                # Updating the referrers balance and getting the updated User object 
                referrer = await update_user(telegram_id=user_referrer_id, balance_increment=balance_increment)
                logger.info(
                    f"User {tg_id} paid {paid_amount}. "
                    f"Referrer {user_referrer_id} credited with {balance_increment} "
                    f"({referrer.ref_cashback_percentage}% cashback)."
                )

                # Balance top up notification
                try:
                    logger.info(f"Notifying a user with id {user_referrer_id} about balance top up")
                    await balance_credit_notify(
                        telegram_id=user_referrer_id,
                        referee=user, 
                        balance_credit=balance_increment, 
                        bot=bot
                        )
                except Exception as e:
                    logger.warning(f"Wasn't able to notify the user with id {user_referrer_id} about his balance top up: {e}")
            else:
                logger.info(f"No referrer for the user {tg_id}")

        elif event == "payment.canceled":
            logger.info(f"Payment canceled: {obj.get('id')}")
            # Optionally, handle cancellations here (refunds, notifications, etc.)

        else:
            logger.warning(f"Unhandled YooKassa event type: {event}")

    except Exception as e:
        logger.error(f"Error handling YooKassa update: {e}")

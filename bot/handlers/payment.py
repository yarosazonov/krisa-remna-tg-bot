import math
from aiogram import Bot

from config import get_logger, get_settings
from bot.services import RemnawaveService, YooKassaService, balance_credit_notify
from db import get_user, update_user, check_payment_processed, add_processed_payment
from helpers import months_to_days

logger = get_logger(__name__)


async def handle_yookassa_update(
    event: str, 
    obj: dict, 
    remnawave_service: RemnawaveService, 
    yookassa_service: YooKassaService, 
    bot: Bot
):
    """
    Handles YooKassa payment events.
    """
    settings = get_settings()
    try:
        if event == "payment.succeeded":
            # 1. Extract Payment ID
            payment_id = obj.get("id")
            if not payment_id:
                logger.error(f"Missing payment ID in payment.succeeded event: {obj}")
                return

            # Idempotency check 
            if await check_payment_processed(payment_id):
                logger.info(f"Payment {payment_id} already processed. Skipping.")
                return

            # 2. Verify with YooKassa API 
            logger.info(f"Verifying payment {payment_id} with YooKassa API...")
            payment_info = await yookassa_service.get_payment_info(payment_id)

            if not payment_info:
                logger.error(f"Verification failed: Could not fetch payment {payment_id} from YooKassa.")
                return

            if payment_info.get("status") != "succeeded":
                logger.warning(f"Verification failed: Payment {payment_id} status is {payment_info.get('status')}, expected 'succeeded'.")
                return
            
            # 3. Use Metadata from API Response
            metadata = payment_info.get("metadata", {})
            tg_id_str = metadata.get("telegram_id")
            subscription_months_str = metadata.get("subscription_months")

            if not tg_id_str or not subscription_months_str:
                logger.error(f"Missing metadata in verified payment {payment_id}: {metadata}")
                return

            try:
                tg_id = int(tg_id_str)
                subscription_months = int(subscription_months_str)
            except ValueError:
                logger.error(f"Invalid metadata values in verified payment {payment_id}: {metadata}")
                return

            # Convert months → days 
            subscription_days = months_to_days(subscription_months) 

            # For simplicity, set traffic and squads defaults; modify as needed
            tg_tag = metadata.get("user_tag")

            logger.info(f"Verified payment {payment_id} for tg_id={tg_id}: +{subscription_days} days")
            
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
                    # Use trusted amount from API
                    paid_amount = payment_info.get("amount_value", 0.0) 
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

            # Mark payment as processed
            await add_processed_payment(payment_id, tg_id, int(paid_amount))
            logger.info(f"Payment {payment_id} marked as processed.")

        elif event == "payment.canceled":
            logger.info(f"Payment canceled: {obj.get('id')}")
            # Optionally, handle cancellations here (refunds, notifications, etc.)

        else:
            logger.warning(f"Unhandled YooKassa event type: {event}")

    except Exception as e:
        logger.error(f"Error handling YooKassa update: {e}", exc_info=True)

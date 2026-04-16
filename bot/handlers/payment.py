import math
from aiogram import Bot

from config import get_logger, get_settings
from bot.services import RemnawaveService, YooKassaService, balance_credit_notify
from db import get_user, update_user, check_payment_processed, add_processed_payment, deduct_balance
from helpers import months_to_days, get_price_map

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
            #
            payment_id = obj.get("id")
            if not payment_id:
                logger.error(f"Missing payment ID in payment.succeeded event: {obj}")
                return

            # Idempotency check 
            if await check_payment_processed(payment_id):
                logger.info(f"Payment {payment_id} already processed. Skipping.")
                return

            # 2. Verify with YooKassa API 
            #
            logger.info(f"Verifying payment {payment_id} with YooKassa API...")
            payment_info = await yookassa_service.get_payment_info(payment_id)

            if not payment_info:
                logger.error(f"Verification failed: Could not fetch payment {payment_id} from YooKassa.")
                return

            if payment_info.get("status") != "succeeded":
                logger.warning(f"Verification failed: Payment {payment_id} status is {payment_info.get('status')}, expected 'succeeded'.")
                return
            
            # 3. Use Metadata from API Response
            #
            metadata = payment_info.get("metadata", {})
            tg_id_str = metadata.get("telegram_id")
            subscription_months_str = metadata.get("subscription_months")

            if not tg_id_str or subscription_months_str is None:
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

            # 4. Validate Payment Amount
            #
            user = await get_user(telegram_id=tg_id)
            
            # Determine Expected Price
            subscription_map = get_price_map(settings)
            expected_price = None
            
            # Find the price for the given number of months
            for sub_key, sub_data in subscription_map.items():
                if sub_data["months"] == subscription_months:
                    expected_price = sub_data["price"]
                    break
            
            if expected_price is None:
                logger.error(f"Payment {payment_id} rejected: Invalid subscription months {subscription_months}.")
                return

            # Calculate Total Value Provided
            # Use trusted amount from API
            paid_amount = payment_info.get("amount_value", 0.0) 
            paid_amount = int(float(paid_amount)) 

            reset_balance = metadata.get("reset_balance")
            is_balance_reset = str(reset_balance).lower() == "true"
            
            # If they requested to reset balance, their current balance is a part of the payment.
            # We check the current balance in the DB, they might spent it in the meantime (race condition) 
            balance_contribution = user.balance if is_balance_reset else 0
            
            total_value_provided = paid_amount + balance_contribution

            # Verify
            if total_value_provided < expected_price:
                 logger.warning(
                     f"SCAM ATTEMPT / PAYMENT ERROR: Payment {payment_id} (tg_id={tg_id}). "
                     f"Expected {expected_price}, but Paid {paid_amount} + Balance {balance_contribution} = {total_value_provided}. "
                     f"Reset Balance: {is_balance_reset}. REJECTING SUBSCRIPTION."
                 )
                 try:
                     await bot.send_message(
                         chat_id=tg_id,
                         text=(
                             f"⚠️ <b>Ошибка активации подписки</b>\n\n"
                             f"Платеж прошел, но итоговая сумма (с учетом баланса) недостаточна для оплаты выбранного тарифа.\n"
                             f"Ожидалось: <b>{expected_price} RUB</b>\n"
                             f"Получено: <b>{total_value_provided} RUB</b>\n\n"
                             "Подписка не активирована. Если вы считаете, что это ошибка, обратитесь в поддержку."
                         ),
                         parse_mode="HTML"
                     )
                 except Exception as exc:
                     logger.error(f"Failed to send rejection notification to {tg_id}: {exc}")
                 return

            logger.info(f"Payment verified: {paid_amount} paid + {balance_contribution} balance >= {expected_price} price.")
            logger.info(f"Verified payment {payment_id} for tg_id={tg_id}: +{subscription_days} days")
            
            # 5. Deduct Balance First 
            #
            reset_balance = metadata.get("reset_balance")
            is_balance_reset = str(reset_balance).lower() == "true"
            balance_deducted = 0

            if is_balance_reset and balance_contribution > 0:
                logger.info(f"Attempting deduction of {balance_contribution} for user {tg_id}")
                if not await deduct_balance(telegram_id=tg_id, amount=balance_contribution):
                    logger.error(f"RACE CONDITION DETECTED: User {tg_id} tried to spend {balance_contribution} but failed deduction.")
                    # Notify user about failure
                    try:
                        await bot.send_message(
                            chat_id=tg_id,
                            text="⚠️ <b>Ошибка оплаты</b>\n\nНе удалось списать средства с баланса (возможно, они уже были потрачены). Обратитесь в поддержку.",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify user {tg_id} about race condition: {e}")
                    return
                balance_deducted = balance_contribution

            # 6. Trigger the payment handling
            #
            if subscription_months == 0:
                try:
                    await remnawave_service.reset_user_traffic(telegram_id=tg_id)
                except Exception as e:
                    logger.error(f"Failed to reset traffic via Remnawave for {tg_id}: {e}. REFUNDING BALANCE.")
                    if balance_deducted > 0:
                        await update_user(telegram_id=tg_id, balance_increment=balance_deducted)
                        logger.info(f"Refunded {balance_deducted} to user {tg_id}")
                    return
            else:
                try:
                    await remnawave_service.handle_payment(
                        tg_id=tg_id,
                        tg_tag=tg_tag,
                        subscription_days=subscription_days
                    )
                except Exception as e:
                    logger.error(f"Failed to grant subscription via Remnawave for {tg_id}: {e}. REFUNDING BALANCE.")
                    if balance_deducted > 0:
                        await update_user(telegram_id=tg_id, balance_increment=balance_deducted)
                        logger.info(f"Refunded {balance_deducted} to user {tg_id}")
                    return

            # Updating referrers internal balance
            user_referrer_id = user.referrer_id

            if user_referrer_id:
                try:
                    referrer =  await get_user(telegram_id=user_referrer_id)

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

                except Exception as e:
                    logger.error(f"Error while processing referral bonus: {e}")
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

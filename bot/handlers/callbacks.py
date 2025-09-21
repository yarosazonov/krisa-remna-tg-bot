from aiogram import types, Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config.logging_config import get_logger
from config.settings import get_settings

from db.db_setup import revoke_trial, get_user
from bot.keyboards.user_keyboards import get_main_menu_keyboard, get_sub_keyboard, get_buy_keyboard, get_trial_keyboard
from bot.middlewares.id_check_middleware import UserIDMiddleware
from bot.services.remnawave_service import RemnawaveService
from bot.services.yookassa_service import YooKassaService

logger = get_logger(__name__)
router = Router()
# Register the middlewares
router.callback_query.middleware(UserIDMiddleware())



# Main menu callback
#
#
@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: types.CallbackQuery, telegram_id: int):
    try:
        logger.info(f"User {telegram_id} started the bot")

        welcome_text = (
            "👋 Добро пожаловать в <b>KrisaVPN</b> bot!"
        )

        user = await get_user(telegram_id=telegram_id)
        keyboard = get_main_menu_keyboard(user.eligible_for_trial)
        await callback.message.edit_text(welcome_text, reply_markup=keyboard, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error handling /start command from user {telegram_id}: {e}")
        await callback.message.edit_text("Извините, что-то пошло не так.")



# Sub menu callback
#
#
@router.callback_query(F.data == "sub_menu")
async def sub_callback(callback: types.CallbackQuery, telegram_id: int, remnawave_service: RemnawaveService) -> None:
    """Handle /status command to check subscription status."""
    try:
        logger.info(f"User {telegram_id} requested subscription status")

        await callback.message.edit_text("🔍 Проверяю статус вашей подписки...")

        # Use module-level service instance

        # API request to the remna panel
        user_data = await remnawave_service.get_formatted_status(telegram_id)

        if user_data is None:
            await callback.message.edit_text(
                "❌ <b>Подписка не найдена</b> ❌\n\n"
                "Активная подписка для вашего Telegram аккаунта не найдена.\n"
                "Обратитесь в поддержку, если считаете, что это ошибка.",
                parse_mode="HTML",
                reply_markup=get_sub_keyboard(is_sub_found=False)
            )
            return

        await callback.message.edit_text(
            f"🔐 <b>Ваша подписка:</b>\n\n{user_data}",
            parse_mode="HTML",
            reply_markup=get_sub_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error handling /status command from user {telegram_id}: {e}")
        await callback.message.edit_text(
            "❌ **Ошибка**\n\n"
            "В данный момент невозможно получить статус подписки.\n"
            "Попробуйте позже или обратитесь в поддержку."
        )



# Buy callback
#
#
@router.callback_query(F.data == "buy_menu")
async def buy_callback(callback: types.CallbackQuery):
    settings = get_settings()
    await callback.message.edit_text(
        "Выберите срок продления подписки:",
        parse_mode="HTML",
        reply_markup=get_buy_keyboard(
            enable_1_month=settings.ENABLE_1_MONTH, 
            enable_3_months=settings.ENABLE_3_MONTHS, 
            enable_6_months=settings.ENABLE_6_MONTHS,
            rub_price_1_month=settings.RUB_PRICE_1_MONTH,
            rub_price_3_months=settings.RUB_PRICE_3_MONTHS,
            rub_price_6_months=settings.RUB_PRICE_6_MONTHS)
    )
    await callback.answer()



# Trial callbacks
#
#
@router.callback_query(F.data == "trial_menu")
async def trial_callback(callback: types.CallbackQuery, telegram_id: int):
    user = await get_user(telegram_id)
    
    await callback.message.edit_text(
        "🐀 Попробуй Крысу бесплатно и без условий!",
        parse_mode="HTML",
        reply_markup=get_trial_keyboard(is_eligible=user.eligible_for_trial)
    )
    await callback.answer()

@router.callback_query(F.data == "trial_menu_used")
async def trial_used_callback(callback: types.CallbackQuery, telegram_id: int, remnawave_service: RemnawaveService):
    if callback.from_user.username:
        user_tag = callback.from_user.username
    else:
        user_tag = 'tg'

    settings = get_settings()

    # Use module-level service instance

    _ = await remnawave_service.grant_trial(
        tg_id=telegram_id, tg_tag=user_tag,
        trial_days=settings.TRIAL_DAYS,
        trial_traffic=settings.TRIAL_TRAFFIC_GB,
        internal_squads=settings.SQUADS)

    await revoke_trial(telegram_id)
    # Creating a custom keyboard on the fly
    keyboard_buttons = [
        [InlineKeyboardButton(text="🔐 Моя подписка", callback_data="sub_menu")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]
    await callback.message.edit_text(
        "🎉 Пробный период активирован!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    )
    await callback.answer()



# Payment callbacks
#
#
@router.callback_query(F.data.startswith("pay_"))
async def payment_callback(callback: types.CallbackQuery, telegram_id: int, yookassa_service: YooKassaService):
    try:
        settings = get_settings()

        # Parse subscription period from callback data
        subscription_period = callback.data.replace("pay_", "")

        # Map subscription periods to prices and descriptions
        subscription_map = {
            "1_month": {
                "months": 1,
                "price": settings.RUB_PRICE_1_MONTH,
                "description": "Подписка на 1 месяц"
            },
            "3_months": {
                "months": 3,
                "price": settings.RUB_PRICE_3_MONTHS,
                "description": "Подписка на 3 месяца"
            },
            "6_months": {
                "months": 6,
                "price": settings.RUB_PRICE_6_MONTHS,
                "description": "Подписка на 6 месяцев"
            }
        }

        if subscription_period not in subscription_map:
            await callback.message.edit_text("❌ Неверный период подписки")
            return

        sub_info = subscription_map[subscription_period]

        await callback.message.edit_text("⏳ Создаю платеж...")
        user_tag = callback.from_user.username
        # Create payment metadata
        metadata = {
            "telegram_id": str(telegram_id),
            "user_tag": str(user_tag),
            "subscription_months": str(sub_info["months"])
        }

        # Create payment
        payment_result = await yookassa_service.create_payment(
            amount=float(sub_info["price"]),
            currency="RUB",
            description=sub_info["description"],
            metadata=metadata
        )

        if not payment_result or payment_result.get("error"):
            error_msg = payment_result.get("internal_message") if payment_result else "Неизвестная ошибка"
            await callback.message.edit_text(
                f"❌ Ошибка создания платежа:\n{error_msg}\n\n"
                "Попробуйте позже или обратитесь в поддержку.",
                reply_markup=get_buy_keyboard(
                    enable_1_month=settings.ENABLE_1_MONTH,
                    enable_3_months=settings.ENABLE_3_MONTHS,
                    enable_6_months=settings.ENABLE_6_MONTHS,
                    rub_price_1_month=settings.RUB_PRICE_1_MONTH,
                    rub_price_3_months=settings.RUB_PRICE_3_MONTHS,
                    rub_price_6_months=settings.RUB_PRICE_6_MONTHS
                )
            )
            return

        confirmation_url = payment_result.get("confirmation_url")
        if not confirmation_url:
            await callback.message.edit_text(
                "❌ Не удалось получить ссылку для оплаты\n\n"
                "Попробуйте позже или обратитесь в поддержку.",
                reply_markup=get_buy_keyboard(
                    enable_1_month=settings.ENABLE_1_MONTH,
                    enable_3_months=settings.ENABLE_3_MONTHS,
                    enable_6_months=settings.ENABLE_6_MONTHS,
                    rub_price_1_month=settings.RUB_PRICE_1_MONTH,
                    rub_price_3_months=settings.RUB_PRICE_3_MONTHS,
                    rub_price_6_months=settings.RUB_PRICE_6_MONTHS
                )
            )
            return

        # Create payment keyboard
        #from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        payment_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=confirmation_url)],
            [InlineKeyboardButton(text="🔍 Проверить оплату", callback_data=f"check_payment_{payment_result['id']}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_menu")]
        ])

        await callback.message.edit_text(
            f"💳 <b>Платеж создан</b>\n\n"
            f"📋 <b>Детали заказа:</b>\n"
            f"• Подписка: {sub_info['description']}\n"
            f"• Сумма: {sub_info['price']} RUB\n"
            f"• ID платежа: <code>{payment_result['id']}</code>\n\n"
            f"Нажмите кнопку ниже для оплаты:",
            parse_mode="HTML",
            reply_markup=payment_keyboard
        )

    except Exception as e:
        logger.error(f"Error handling payment callback from user {telegram_id}: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при создании платежа\n\n"
            "Попробуйте позже или обратитесь в поддержку."
        )
    await callback.answer()


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_callback(callback: types.CallbackQuery, telegram_id: int, yookassa_service: YooKassaService):
    try:
        # Extract payment ID from callback data
        payment_id = callback.data.replace("check_payment_", "")

        logger.info(f"User {telegram_id} checking payment status for payment_id: {payment_id}")

        await callback.message.edit_text("⏳ Проверяю статус платежа...")

        # Check if YooKassa service is properly configured
        if not yookassa_service.configured:
            logger.error("YooKassa service is not configured")
            await callback.message.edit_text(
                "❌ Сервис платежей временно недоступен\n\n"
                "Обратитесь в поддержку."
            )
            return

        # Get payment info from YooKassa
        logger.info(f"Fetching payment info for payment_id: {payment_id}")
        payment_info = await yookassa_service.get_payment_info(payment_id)

        logger.info(f"Payment info result: {payment_info}")

        if not payment_info:
            logger.error(f"get_payment_info returned None for payment_id: {payment_id}")
            await callback.message.edit_text(
                "❌ Не удалось получить информацию о платеже\n\n"
                f"ID платежа: <code>{payment_id}</code>\n"
                "Попробуйте позже или обратитесь в поддержку.",
                parse_mode="HTML"
            )
            return

        

        if payment_info.get("paid") and payment_info.get("status") == "succeeded":
            # Payment successful - here you would typically activate the subscription
            # For now, just show success message
            await callback.message.edit_text(
                "✅ <b>Оплата прошла успешно!</b>\n\n"
                f"💳 ID платежа: <code>{payment_id}</code>\n"
                f"💰 Сумма: {payment_info.get('amount_value')} {payment_info.get('amount_currency')}\n\n"
                "Ваша подписка будет активирована в ближайшее время.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                ])
            )
        else:
            # Payment not yet completed
            status_text = {
                "pending": "ожидает оплаты",
                "waiting_for_capture": "ожидает подтверждения",
                "canceled": "отменен"
            }.get(payment_info.get("status"), payment_info.get("status", "неизвестен"))

            # Create keyboard based on payment status
            keyboard_buttons = []

            # Add payment button for pending payments
            if payment_info.get("status") == "pending":
                confirmation_url = payment_info.get("confirmation_url")
                if confirmation_url:
                    keyboard_buttons.append([InlineKeyboardButton(text="💳 Оплатить", url=confirmation_url)])

            keyboard_buttons.append([InlineKeyboardButton(text="🔍 Проверить еще раз", callback_data=f"check_payment_{payment_id}")])
            keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Назад к покупкам", callback_data="buy_menu")])

            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

            await callback.message.edit_text(
                f"⏳ <b>Статус платежа:</b> {status_text}\n\n"
                f"💳 ID платежа: <code>{payment_id}</code>\n"
                f"💰 Сумма: {payment_info.get('amount_value')} {payment_info.get('amount_currency')}\n\n"
                "Если вы уже оплатили, подождите несколько минут и проверьте снова.",
                parse_mode="HTML",
                reply_markup=keyboard
            )

    except Exception as e:
        logger.error(f"Error checking payment {callback.data} for user {telegram_id}: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при проверке платежа\n\n"
            "Попробуйте позже или обратитесь в поддержку."
        )
    await callback.answer()
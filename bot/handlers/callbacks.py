from aiogram import types, Router, F
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
        "Попробуй крысу!",
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
    await callback.message.edit_text(
        "Ты попробовал крысу!",
        parse_mode="HTML",
        reply_markup=get_trial_keyboard(is_eligible=False)
    )
    await callback.answer()
from aiogram import types, Router, F
from config.logging_config import get_logger
from config.settings import get_settings
from bot.services.remnawave_service import RemnawaveService

from db.db_setup import revoke_trial, get_user
from bot.keyboards.user_keyboards import get_main_menu_keyboard, get_sub_keyboard, get_buy_keyboard, get_trial_keyboard

logger = get_logger(__name__)
router = Router()



# Main menu callback
#
#
@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: types.CallbackQuery):
    try:
        user_id = callback.from_user.id
        
        logger.info(f"User {user_id} started the bot")

        welcome_text = (
            "👋 Добро пожаловать в <b>KrisaVPN</b> bot!"
        )

        user = await get_user(telegram_id=user_id)
        keyboard = get_main_menu_keyboard(user.eligible_for_trial)
        await callback.message.edit_text(welcome_text, reply_markup=keyboard, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error handling /start command from user {user_id}: {e}")
        await callback.message.edit_text("Извините, что-то пошло не так.")



# Sub menu callback
#
#
@router.callback_query(F.data == "sub_menu")
async def sub_callback(callback: types.CallbackQuery) -> None:
    """Handle /status command to check subscription status."""
    try:
        telegram_id = callback.from_user.id
        logger.info(f"User {telegram_id} requested subscription status")

        await callback.message.edit_text("🔍 Проверяю статус вашей подписки...")

        settings = get_settings()
        remnawave_service = RemnawaveService(
            api_url=settings.REMNAWAVE_API_URL,
            api_token=settings.REMNAWAVE_API_TOKEN
        )

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
        logger.error(f"Error handling /status command from user {callback.from_user.id}: {e}")
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
    await callback.message.edit_text(
        "Не продаётся!",
        parse_mode="HTML",
        reply_markup=get_buy_keyboard()
    )
    await callback.answer()



# Trial callbacks
#
#
@router.callback_query(F.data == "trial_menu")
async def trial_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    
    await callback.message.edit_text(
        "Попробуй крысу!",
        parse_mode="HTML",
        reply_markup=get_trial_keyboard(is_eligible=user.eligible_for_trial)
    )
    await callback.answer()

@router.callback_query(F.data == "trial_menu_used")
async def trial_used_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if callback.from_user.username:
        user_tag = callback.from_user.username
    else:
        user_tag = 'tg'
    
    settings = get_settings()

    remnawave_service = RemnawaveService(
            api_url=settings.REMNAWAVE_API_URL,
            api_token=settings.REMNAWAVE_API_TOKEN
        )

    result = await remnawave_service.grant_trial(tg_id=user_id, tg_tag=user_tag, trial_days=settings.TRIAL_DAYS, trial_traffic=settings.TRIAL_TRAFFIC_GB, internal_squads=settings.SQUADS)
    
    await revoke_trial(user_id)
    await callback.message.edit_text(
        "Ты попробовал крысу!",
        parse_mode="HTML",
        reply_markup=get_trial_keyboard(is_eligible=False)
    )
    await callback.answer()
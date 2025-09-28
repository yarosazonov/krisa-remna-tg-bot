from aiogram import types, Router, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.deep_linking import create_start_link
from config.logging_config import get_logger
from config.settings import get_settings

from db.db_setup import revoke_trial, get_user, get_referees, update_user
from bot.keyboards.user_keyboards import get_main_menu_keyboard, get_sub_keyboard, get_buy_keyboard, get_trial_keyboard
from bot.middlewares.id_check_middleware import UserIDMiddleware
from bot.services.remnawave_service import RemnawaveService
from bot.services.yookassa_service import YooKassaService
from bot.handlers.commands import WELCOME_TEXT
from helpers.helpers import get_subscription_map, months_to_days

logger = get_logger(__name__)
settings = get_settings()
router = Router()
# Register the middlewares
router.callback_query.middleware(UserIDMiddleware())



# ==================
# Main menu callback
# ==================
@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: types.CallbackQuery, telegram_id: int):
    try:
        logger.info(f"User {telegram_id} started the bot")

        user = await get_user(telegram_id=telegram_id)
        keyboard = get_main_menu_keyboard(user.eligible_for_trial)
        await callback.message.edit_text(WELCOME_TEXT, reply_markup=keyboard, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error handling /start command from user {telegram_id}: {e}")
        await callback.message.edit_text("Извините, что-то пошло не так.")

    await callback.answer()



# =================
# Sub menu callback
# =================
@router.callback_query(F.data == "sub_menu")
async def sub_callback(callback: types.CallbackQuery, telegram_id: int, remnawave_service: RemnawaveService) -> None:
    """Handle /status command to check subscription status."""
    try:
        logger.info(f"User {telegram_id} requested subscription status")
        
        await callback.answer(text="🔍 Проверяю статус вашей подписки...", show_alert=False)
        # await callback.message.edit_text("🔍 Проверяю статус вашей подписки...")

        # Use module-level service instance

        # API request to the remna panel
        user_data = await remnawave_service.get_formatted_status(telegram_id)

        if user_data is None:
            await callback.message.edit_text(
                "⛔ <b>Подписка не найдена</b>\n\n"
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



# ========================
# Update sub link callback
# ========================
@router.callback_query(F.data == "update_sub")
async def sub_callback(callback: types.CallbackQuery) -> None:
    """Regenerates the sub link"""
    keyboard = [
        [InlineKeyboardButton(text="☑ Да", callback_data="confirm_update_sub")],        
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="sub_menu")]
    ]

    await callback.message.edit_text(
        "🔐 <b>Генерация новой ссылки</b>\n\n"
        "📡 <b>Почему стоит обновить ссылку?</b>\n"
        "Это полезно, если вы считаете, что кто-то пользуется вашей ссылкой без разрешения.\n\n"
        "⚠ <b>После обновления:</b>\n"
        "Придётся вручную добавить новую ссылку на всех устройствах.\n\n"
        "❓ Хотите продолжить?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_update_sub")
async def confirm_update_sub(callback: types.CallbackQuery, telegram_id: int, remnawave_service: RemnawaveService):
    await remnawave_service.update_subscription(telegram_id=telegram_id)
    await callback.answer("Ссылка успешно обновлена!", show_alert=True)



# ============
# Buy callback
# ============
@router.callback_query(F.data == "buy_menu")
async def buy_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Оплачивая подписку, вы получаете:\n\n"
        "🌍 Доступ ко всем серверам\n"
        "📦 250 ГБ трафика ежемесячно\n\n"
        "💳 Выберите срок продления подписки:",
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



# ================
# Traffic question
# ================
@router.callback_query(F.data == "traffic_question")
async def traffic_question_callback(callback: types.CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_menu")]
    ]

    await callback.message.edit_text(
        "📡 <b>Почему есть ограничение по трафику?</b>\n\n"
        "🛡️ Ограничение помогает защищать сеть от злоумышленников и "
        "поддерживать стабильную высокую скорость для всех пользователей.\n\n"
        "📊 Практика показывает, что при активном использовании интернета "
        "с нескольких устройств, расход трафика редко превышает "
        "<b>100 ГБ в месяц</b>. Поэтому 250 ГБ - это лимит с большим запасом",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

# ===============
# Trial callbacks
# ===============
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
    user_tag = callback.from_user.username or "tg"

    # Use module-level service instance

    _ = await remnawave_service.grant_trial(tg_id=telegram_id, tg_tag=user_tag)

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



# ========================
# Payment callbacks
# ========================
# Step 1: Prepare payment
# ========================
@router.callback_query(F.data.startswith("prepare_"))
async def payment_prep_callback(callback: types.CallbackQuery, telegram_id: int, yookassa_service: YooKassaService):
    try:
        # Parse subscription period from callback data
        subscription_period = callback.data.replace("prepare_", "")

        subscription_map = get_subscription_map(settings)

        if subscription_period not in subscription_map:
            await callback.message.edit_text("❌ Неверный период подписки")
            return
        
        keys = [
            [InlineKeyboardButton(text="✅ Оплатить полную сумму", callback_data=f"pay_{subscription_period}_full")]
        ]

        sub_info = subscription_map[subscription_period]
        user = await get_user(telegram_id=telegram_id)
        balance = user.balance 

        # Finish building the keyboard
        if balance > 0:
            keys.append([InlineKeyboardButton(text="💱 Списать средства с баланса", callback_data=f"pay_{subscription_period}_part")])
        keys.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_menu")])

        await callback.message.edit_text(
            f"📋 <b>Детали заказа:</b>\n\n"
            f"• {sub_info['description']}\n"
            f"• Сумма: <b>{sub_info['price']} RUB</b>\n"
            f"• Текущий баланс: <b>{balance} RUB</b>\n",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keys)
        )

    except Exception as e:
        logger.error(f"Error creating order for {telegram_id}: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при подготовке платежа\n\n"
            "Попробуйте позже или обратитесь в поддержку."
        )
    await callback.answer()

# ======================
# Step 2: Create payment
# ======================
@router.callback_query(F.data.startswith("pay_"))
async def payment_callback(
    callback: types.CallbackQuery, 
    telegram_id: int, 
    remnawave_service: RemnawaveService, 
    yookassa_service: YooKassaService
    ):
    try:
        user_tag = callback.from_user.username or "tg"
        subscription_map = get_subscription_map(settings)

        # Parse callback: pay_1_month_full → ["pay", "1_month", "full"]
        parts = callback.data.split("_")
        if len(parts) < 3:
            await callback.message.edit_text("❌ Неверный формат данных оплаты")
            return

        subscription_period = "_".join(parts[1:-1])  # e.g. "1_month"
        method = parts[-1]                           # "full" or "part"

        if subscription_period not in subscription_map:
            await callback.message.edit_text("❌ Неверный период подписки")
            return

        sub_info = subscription_map[subscription_period]
        user = await get_user(telegram_id=telegram_id)
        balance = user.balance
        price = sub_info["price"]

         # Handle full vs partial payment
        if method == "part":
            if balance >= price:
                # User can cover fully with balance
                keys = [
                    [InlineKeyboardButton(text="🏡 Главное меню", callback_data="main_menu")]
                ]
                await remnawave_service.handle_payment(
                    tg_id=telegram_id, 
                    tg_tag=user_tag, 
                    subscription_days=months_to_days(sub_info["months"])
                    )
                user_db = await update_user(telegram_id=telegram_id, balance_increment=-price)
                await callback.message.edit_text(
                    f"✅ {sub_info['description']} успешно оплачена!\n\n"
                    f"Новый баланс: <b>{user_db.balance} RUB</b>",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keys)
                )
                return
            else:
                # Deduct balance, pay the rest
                amount_to_charge = price - balance 
                reset_balance = True
        else:
            # Full payment
            reset_balance = False
            amount_to_charge = price


        await callback.answer(text="⏳ Создаю платеж...", show_alert=False)
        # await callback.message.edit_text("⏳ Создаю платеж...")

        # Create payment metadata
        metadata = {
            "telegram_id": str(telegram_id),
            "user_tag": str(user_tag),
            "subscription_months": str(sub_info["months"]),
            "payment_method": method,
            "reset_balance": reset_balance
        }

        # Create YooKassa  payment
        payment_result = await yookassa_service.create_payment(
            amount=float(amount_to_charge),
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

        # Payment keyboard
        payment_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=confirmation_url)],
            [InlineKeyboardButton(text="🔍 Проверить оплату", callback_data=f"check_payment_{payment_result['id']}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_menu")]
        ])

        await callback.message.edit_text(
            f"💳 <b>Платеж создан:</b>\n\n"
            f"• {sub_info['description']}\n"
            f"• Сумма к оплате: <b>{amount_to_charge} RUB</b>\n"
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



# =============
# Check payment
# =============
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



# ================
# Bonuses callback
# ================
@router.callback_query(F.data == "bonus_menu")
async def bonus_menu_callback(callback: types.CallbackQuery, telegram_id: int, bot: Bot):

    # Generate referral link
    referral_link = await create_start_link(bot, telegram_id)

    keys = [
        [InlineKeyboardButton(text="🤝 Мои рефералы", callback_data="check_referees")],
        [InlineKeyboardButton(text="📑 Правила вывода", callback_data="withdrawal_rules")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]

    await callback.message.edit_text(
        "🤝 <b>Приглашайте друзей и получайте бонусы!</b>\n\n"
        "💰 Вы получаете <b>10% от их покупок</b> на свой баланс.\n"
        "📌 Бонусы можно потратить на <b>оплату подписки</b> или <b>вывести</b>.\n\n"
        "🔗 <b>Как пригласить?</b>\n"
        "Поделитесь с человеком вашей <b>реферальной ссылкой</b>.\n"
        "Если он впервые запустит бот — "
        "он станет вашим рефералом!\n\n"
        f"👉 <b>Реферальная ссылка:</b>\n<code>{referral_link}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keys)
    )

    await callback.answer()



# =======================
# Check referees callback
# =======================
@router.callback_query(F.data == "check_referees")
async def check_referees_callback(callback: types.CallbackQuery, telegram_id: int):
    referees_dict = await get_referees(telegram_id)

    if referees_dict:
        # Format each referee as "Tag: @username, Id: tid" on a new line
        referees_text = "\n".join(
            f"Tag: @{uname}; Id: <code>{tid}</code>" if uname else f"Tag: None; Id: <code>{tid}</code>"
            for tid, uname in referees_dict.items()
        )
    else:
        referees_text = "У вас пока нет рефералов"
    
    keys = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="bonus_menu")]
    ]

    await callback.message.edit_text(
        f"🧍‍♂️ Ваши рефералы:\n{referees_text}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keys)
    )
    await callback.answer()


# =========================
# Withdrawal rules callback
# =========================
@router.callback_query(F.data == "withdrawal_rules")
async def withdrawal_rules_callback(callback: types.CallbackQuery):
    keys = [
            [InlineKeyboardButton(text="💰 Баланс", callback_data="balance_menu")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="bonus_menu")]
        ]

    text = (
        "💵 <b>Вывод средств</b>\n\n"
        "Вы можете запросить вывод средств, если ваш баланс ≥ <b>50₽</b>.\n"
        "Перевод будет выполнен не позднее полуночи следующего дня."
    )


    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keys)
    )
    await callback.answer()


# ================
# Balance callback
# ================
@router.callback_query(F.data == "balance_menu")
async def check_referees_callback(callback: types.CallbackQuery, telegram_id: int):
    keys = [
        [InlineKeyboardButton(text="💬 Запросить вывод", url="https://t.me/yarosazonov")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]
    try:
        user = await get_user(telegram_id=telegram_id)
        balance = user.balance 
        await callback.message.edit_text(
            f"💵 Ваш баланс: {balance} RUB",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keys)
        )

    except Exception as e:
        logger.error(f"Error retrieving balance for user {telegram_id}: {e}")
    await callback.answer()
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_settings

settings = get_settings()

def get_main_menu_keyboard(show_trial: bool):
    keyboard = [
        [InlineKeyboardButton(text="🔐 Моя подписка", callback_data="sub_menu")],
        [InlineKeyboardButton(text="🔥 Купить", callback_data="buy_menu")],
        [
            InlineKeyboardButton(text="🤑 Бонусы 10%", callback_data="bonus_menu"),
            InlineKeyboardButton(text="💰 Баланс", callback_data="balance_menu")
        ]
    ]

    if settings.SUPPORT_TG_LINK:
        keyboard.append([InlineKeyboardButton(text="💬 Поддержка", url=settings.SUPPORT_TG_LINK)])

    if show_trial:
        keyboard.insert(1, [InlineKeyboardButton(text="☀ Активировать пробный период", callback_data="trial_menu")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)



def get_buy_keyboard(enable_1_month: bool, enable_3_months: bool, enable_6_months: bool, rub_price_1_month: int, rub_price_3_months: int, rub_price_6_months: int, currency: str = 'RUB'):
    keyboard = [
        [InlineKeyboardButton(text="❓ Почему трафик ограничен?", callback_data="traffic_question")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]

    if enable_1_month:
        keyboard.insert(0, [InlineKeyboardButton(text=f"💵 1 месяц: {rub_price_1_month} {currency}", callback_data="prepare_1_month")])
    if enable_3_months:
        keyboard.insert(1, [InlineKeyboardButton(text=f"💰 3 месяца: {rub_price_3_months} {currency}", callback_data="prepare_3_months")])
    if enable_6_months:
        keyboard.insert(2, [InlineKeyboardButton(text=f"👑 6 месяцев: {rub_price_6_months} {currency}", callback_data="prepare_6_months")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)



def get_sub_keyboard(is_sub_found: bool = True):
    keyboard = [        
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]

    if is_sub_found:
        keyboard.insert(0, [InlineKeyboardButton(text="🔒 Безопасность", callback_data="security_menu")])
    else:
        settings = get_settings()
        if settings.SUPPORT_TG_LINK:
            keyboard.insert(0, [InlineKeyboardButton(text="💬 Написать в поддержку", url=settings.SUPPORT_TG_LINK)])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_security_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="🐣 Обновить подписку", callback_data="update_sub")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="sub_menu")],
        [InlineKeyboardButton(text="🏡 Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)



# Trial menu keyboard
#
#
def get_trial_keyboard(is_eligible: bool):
    keyboard = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]

    if is_eligible:
        keyboard.insert(0, [InlineKeyboardButton(text="✅ Активировать пробный период", callback_data="trial_menu_used")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)




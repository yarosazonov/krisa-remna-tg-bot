from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton



def get_main_menu_keyboard(show_trial: bool):
    keyboard = [
        [InlineKeyboardButton(text="🔐 Моя подписка", callback_data="sub_menu")],
        [InlineKeyboardButton(text="🔥 Купить", callback_data="buy_menu")],
        [InlineKeyboardButton(text="💬 Написать в поддержку", url="https://t.me/yarosazonov")],
        [InlineKeyboardButton(text="🔔 Канал", url="https://t.me/krisavpn")]
    ]

    if show_trial:
        keyboard.insert(1, [InlineKeyboardButton(text="☀ Активировать пробный период", callback_data="trial_menu")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)



def get_buy_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ])



def get_sub_keyboard(is_sub_found: bool = True):
    keyboard = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]

    if not is_sub_found:
        keyboard.insert(0, [InlineKeyboardButton(text="💬 Написать в поддержку", url="https://t.me/yarosazonov")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_trial_keyboard(is_eligible: bool):
    keyboard = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
    ]

    if is_eligible:
        keyboard.insert(0, [InlineKeyboardButton(text="✅ Юзануть триалку", callback_data="trial_menu_used")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

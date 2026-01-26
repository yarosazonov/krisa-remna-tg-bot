from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
import logging

from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)



async def balance_credit_notify(bot: Bot, telegram_id: int, referee, balance_credit: int):
    """
    Notify user that their balance has been credited.
    """
    keyboard = [
        [InlineKeyboardButton(text="💰 Текущий баланс", callback_data="balance_menu")]
    ]

    message_text = (
        f"💳 @{referee.telegram_username} оплатил подписку\n"
        f"🎉 Ваш баланс пополнен на <b>{balance_credit} RUB</b>"
    )

    try:
        await bot.send_message(chat_id=telegram_id, text=message_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        logger.info(f"Sent balance credit notification to user {telegram_id} (+{balance_credit} RUB).")
    except TelegramForbiddenError:
        logger.warning(f"Cannot send message to user {telegram_id}: blocked the bot.")
    except TelegramRetryAfter as e:
        logger.error(f"Rate limited when sending to {telegram_id}, retry after {e.retry_after} seconds.")
    except Exception as e:
        logger.error(f"Failed to send balance notification to {telegram_id}: {e}")



async def remnawave_webhook_notification(bot: Bot, telegram_id:int, event: str):
    # Message construction based on the event
    message_text = None
    
    # Message keyboard
    keyboard_buttons = []
    keyboard_buttons.append([InlineKeyboardButton(text="💬 Написать в поддержку", url="https://t.me/yarosazonov")])
    if event in ("user.expires_in_24_hours", "user.expired"):
        keyboard_buttons.insert(0, [InlineKeyboardButton(text="🔥 Продлить подписку", callback_data="buy_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    # Message text
    if event == "user.expires_in_24_hours":
        message_text = ("✋ Добрый день!\n" 
        "Через <b>24 часа</b> ваша подписка истекает, не забудьте продлить!🤝")
    elif event == "user.expired":
        message_text = ("🔔 Здравствуйте, ваша подписка только что истекла!\n"
        "Надеюсь что вы довольны сервисом и останетесь с нами.\n"
        "Если у вас есть замечания, пожалуйста, напишите в поддержку.\nХорошего дня!🎈"
        )
    elif event == "user.limited":
        message_text = ("🔔 Добрый день! У вас кончился траффик.🤯\nЕсли вы хотите приобрести дополнительный пакет - обратитесь в поддержку🤝")

    # Sending the message
    await bot.send_message(chat_id=int(telegram_id), text=message_text, parse_mode="HTML", reply_markup=keyboard)



async def send_backup_to_admin(bot: Bot, backup_path: str):
    """
    Sends the encrypted backup file to the admin.
    """
    try:
        backup_file = FSInputFile(backup_path)
        await bot.send_document(
            chat_id=settings.ADMIN_ID,
            document=backup_file,
            caption=f"📦 Daily Backup"
        )
        logger.info(f"Backup sent to admin {settings.ADMIN_ID}")
    except Exception as e:
        logger.error(f"Failed to send backup to admin: {e}")
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



async def remnawave_webhook_notification(bot: Bot, telegram_id: int, event: str, meta: dict = None):
    # Message construction based on the event
    message_text = None
    is_extension_relevant = False

    if event == "user.expiration":
        expiration = meta.get("expiration") if meta else None
        if expiration is not None and expiration < 0:
            hours = abs(expiration)
            if hours == 24:
                message_text = (
                    "✋ Добрый день!\n"
                    "Через <b>24 часа</b> ваша подписка истекает, не забудьте продлить!🤝"
                )
            elif hours == 72:
                message_text = (
                    "✋ Добрый день!\n"
                    "Через <b>3 дня</b> ваша подписка истекает, не забудьте продлить!🤝"
                )
            else:
                message_text = (
                    f"✋ Добрый день!\n"
                    f"Через <b>{hours} ч.</b> ваша подписка истекает, не забудьте продлить!🤝"
                )
            is_extension_relevant = True
        elif expiration is not None and expiration > 0:
            message_text = (
                f"🔔 Здравствуйте, ваша подписка истекла <b>{expiration} ч.</b> назад.\n"
                "Надеюсь что вы довольны сервисом и останетесь с нами.\n"
                "Если у вас есть замечания, пожалуйста, напишите в поддержку.\nХорошего дня!🎈"
            )
            is_extension_relevant = True
    elif event == "user.expired":
        message_text = (
            "🔔 Здравствуйте, ваша подписка только что истекла!\n"
            "Надеюсь что вы довольны сервисом и останетесь с нами.\n"
            "Если у вас есть замечания, пожалуйста, напишите в поддержку.\nХорошего дня!🎈"
        )
        is_extension_relevant = True
    elif event == "user.limited":
        message_text = (
            "🔔 Добрый день! У вас кончился траффик.🤯\n"
            "Если вы хотите приобрести дополнительный пакет - обратитесь в поддержку🤝"
        )

    if not message_text:
        logger.warning(f"Unhandled remnawave webhook event: {event}")
        return

    # Message keyboard
    keyboard_buttons = []
    keyboard_buttons.append([InlineKeyboardButton(text="💬 Написать в поддержку", url="https://t.me/yarosazonov")])
    if is_extension_relevant:
        keyboard_buttons.insert(0, [InlineKeyboardButton(text="🔥 Продлить подписку", callback_data="buy_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    # Sending the message
    try:
        await bot.send_message(chat_id=int(telegram_id), text=message_text, parse_mode="HTML", reply_markup=keyboard)
        logger.info(f"Sent webhook notification to user {telegram_id} for event {event}.")
    except TelegramForbiddenError:
        logger.warning(f"Cannot send webhook notification to user {telegram_id}: blocked the bot.")
    except TelegramRetryAfter as e:
        logger.error(f"Rate limited when sending webhook notification to {telegram_id}, retry after {e.retry_after} seconds.")
    except Exception as e:
        logger.error(f"Failed to send webhook notification to {telegram_id}: {e}")



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
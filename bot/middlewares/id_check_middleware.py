from aiogram import types
from aiogram import BaseMiddleware

class UserIDMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        """
        Attaches telegram_id to the data dict for any event that has a user.
        """
        telegram_id = None

        # If the event is a message (commands included)
        if isinstance(event, types.Message):
            telegram_id = event.from_user.id

        # If the event is a callback query
        elif isinstance(event, types.CallbackQuery):
            telegram_id = event.from_user.id

        # Add telegram_id to data if found
        if telegram_id:
            data['telegram_id'] = telegram_id

        # Call the next handler
        return await handler(event, data)

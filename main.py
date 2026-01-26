import uvicorn
import asyncio

from config import get_settings, setup_logging
from app.app_bot import create_app
from db import init_db



settings = get_settings()
setup_logging(settings.LOGGING_LVL)
fastapi_app = create_app(settings)

if __name__ == '__main__':
    asyncio.run(init_db())
    uvicorn.run(fastapi_app, host=settings.HOST, port=settings.PORT)
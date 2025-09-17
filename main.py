import uvicorn
from config.settings import get_settings
from config.logging_config import setup_logging
from app.app_bot import create_app

setup_logging()

settings = get_settings()
fastapi_app = create_app(settings)

if __name__ == '__main__':
    uvicorn.run(fastapi_app, host=settings.HOST, port=settings.PORT)
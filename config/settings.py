from config.logging_config import get_logger
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError
from typing import Optional

logger = get_logger(__name__)



class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_ID: int
    DOMAIN: str
    WEBHOOK_PATH: str
    PORT: int
    HOST: str
    SQUADS: str
    TRIAL_DAYS: int
    TRIAL_TRAFFIC_GB: int
    REMNAWAVE_API_URL: str
    REMNAWAVE_API_TOKEN: str

    # decorator that let's call the method like an attribute
    @property
    def WEBHOOK_URL(self) -> str:
        return f"{self.DOMAIN.rstrip('/')}{self.WEBHOOK_PATH}"

    # .env Should be located relative to the python file which calls get_settings().
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        try:
            _settings_instance = Settings()

        except ValidationError as e:
            logger.critical(f"Pydantic validation error while loading settings: {e}")

            raise SystemExit(f"CRITICAL SETTINGS ERROR: {e}. Please check your .env file and Settings model.")
    return _settings_instance
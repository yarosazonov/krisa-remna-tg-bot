from config.logging_config import get_logger  # Use direct import to avoid circular import
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError
from typing import Optional

logger = get_logger(__name__)



class Settings(BaseSettings):
    LOGGING_LVL: str
    # Bot specific
    BOT_TOKEN: str
    ADMIN_ID: int
    SUPPORT_TG_LINK: str
    CHANNEL_TAG: str

    # FastAPI
    BOT_DOMAIN: str
    TG_WEBHOOK_PATH: str
    TG_WEBHOOK_SECRET: str
    YOOKASSA_WEBHOOK_PATH: str
    PORT: int
    HOST: str = '0.0.0.0'

    # Remna
    REMNAWAVE_PANEL_DOMAIN: str
    REMNAWAVE_API_TOKEN: str
    SQUADS: str
    AVAILABLE_SERVERS: str
    REMNAWAVE_WEBHOOK_PATH: str
    REMNAWAVE_WEBHOOK_SECRET_HEADER: str

    # Trial specs
    TRIAL_DAYS: int
    TRIAL_TRAFFIC_GB: int

    # YooKassa payment system settings
    YOOKASSA_SHOP_ID: Optional[str] = None
    YOOKASSA_SECRET_KEY: Optional[str] = None
    YOOKASSA_RETURN_URL: Optional[str] = None
    YOOKASSA_DEFAULT_RECEIPT_EMAIL: Optional[str] = None
    YOOKASSA_VAT_CODE: int = 1
    YOOKASSA_PAYMENT_MODE: str = "full_payment"
    YOOKASSA_PAYMENT_SUBJECT: str = "service"

    # Subscription parameters
    MONTHLY_TRAFFIC_GB: int
    ENABLE_1_MONTH: bool
    RUB_PRICE_1_MONTH: int

    ENABLE_3_MONTHS: bool
    RUB_PRICE_3_MONTHS: int

    ENABLE_6_MONTHS: bool
    RUB_PRICE_6_MONTHS: int

    # decorator that let's call the method like an attribute
    @property
    def TG_WEBHOOK_URL(self) -> str:
        return f"https://{self.BOT_DOMAIN}{self.TG_WEBHOOK_PATH}"

    @property
    def REMNAWAVE_API_URL(self) -> str:
        return f"https://{self.REMNAWAVE_PANEL_DOMAIN}/api"

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
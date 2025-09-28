from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from config.logging_config import get_logger



logger = get_logger(__name__)

BYTES_IN_GB = 1024 ** 3
BYTES_IN_MB = 1024 ** 2

def bytes_to_gb(bytes_value: int) -> float:
    return bytes_value / BYTES_IN_GB

def gb_to_bytes(gb_value: float) -> int:
    return int(gb_value * BYTES_IN_GB)

def mb_to_bytes(mb_value: float) -> int:
    return int(mb_value * BYTES_IN_MB)



def get_subscription_map(settings):
    return {
        "1_month": {
            "months": 1,
            "price": settings.RUB_PRICE_1_MONTH,
            "description": "Подписка на 1 месяц"
        },
        "3_months": {
            "months": 3,
            "price": settings.RUB_PRICE_3_MONTHS,
            "description": "Подписка на 3 месяца"
        },
        "6_months": {
            "months": 6,
            "price": settings.RUB_PRICE_6_MONTHS,
            "description": "Подписка на 6 месяцев"
        }
    }



def months_to_days(months:int) -> int:
    """
    Returns the amount of days in monts provided

    1 month = 30 days
    """
    return months * 30



def format_subscription_status(user_data: Dict[str, Any]) -> str:
    try:
        username = user_data.get('username', 'Н/Д')
        status = user_data.get('status', 'UNKNOWN')

        # Format basic info
        status_text = f"Пользователь: <b>{username}</b>\n"
        if status == "ACTIVE":
            status_text += "Статус: ✅ <b>Активна</b>\n"
        elif status == "INACTIVE":
            status_text += "Статус: ❌ <b>Неактивна</b>\n"
        else:
            status_text += f"Статус: {status}\n"
        # Add expiry date if available
        if 'expireAt' in user_data and user_data['expireAt']:
            try:
                # Parse ISO format date
                expire_date = datetime.fromisoformat(user_data['expireAt'].replace('Z', '+00:00'))
                # Convert to UTC+3
                utc3 = timezone(timedelta(hours=3))
                expire_date_utc3 = expire_date.astimezone(utc3)
                status_text += f"Истекает: {expire_date_utc3.strftime('<b>%d.%m.%Y</b> (%H:%M UTC+3)')}\n"
            except ValueError:
                status_text += f"Истекает: {user_data['expireAt']}\n"

        # Calculate remaining traffic if limited
        if 'trafficLimitBytes' in user_data:
            traffic_limit = user_data['trafficLimitBytes']
            if traffic_limit and traffic_limit > 0:
                # Convert bytes to GB
                traffic_limit_gb = bytes_to_gb(traffic_limit)
                used_traffic = user_data.get('usedTrafficBytes', 0)
                used_traffic_gb = bytes_to_gb(used_traffic)
                status_text += f"\nРасход трафика: <b>{used_traffic_gb:.2f}</b> из <b>{traffic_limit_gb:.2f}</b> ГБ\n"
            else:
                status_text += f"Лимит трафика: <b>Безлимитный</b>\n"

        # Output the sub link
        if 'subscriptionUrl' in user_data:
            sub_link = user_data['subscriptionUrl']
            status_text += f"\n⚙ <b>Ссылка на подключение:</b>\n{sub_link}"
        else:
            logger.error(f"Wasn't able to retrieve the user's sub page")

        return status_text

    except Exception as e:
        logger.error(f"Error formatting subscription status: {e}")
        return "❌ Ошибка при форматировании информации о подписке"
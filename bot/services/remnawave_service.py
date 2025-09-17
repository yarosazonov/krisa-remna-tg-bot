import httpx
from typing import Optional, Dict, Any
from config.logging_config import get_logger

logger = get_logger(__name__)


class RemnawaveService:
    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.api_url}/api/users/by-telegram-id/{telegram_id}"
                logger.info(f"Fetching user data for telegram_id: {telegram_id}")

                response = await client.get(url, headers=self.headers, timeout=10.0)

                if response.status_code == 200:
                    # Parsing the response body as JSON and return the result as a native Python object
                    response_data = response.json()

                    # API returns {"response": [user_data]} format
                    if 'response' in response_data and response_data['response']:
                        user_data = response_data['response'][0]  # Get first user from array
                        logger.info(f"Successfully fetched user data for telegram_id: {telegram_id}")
                        return user_data
                    else:
                        logger.info(f"User not found for telegram_id: {telegram_id}")
                        return None
                elif response.status_code == 404:
                    logger.info(f"User not found for telegram_id: {telegram_id}")
                    return None
                else:
                    logger.error(f"API request failed with status {response.status_code}: {response.text}")
                    return None

        except httpx.TimeoutException:
            logger.error(f"Timeout while fetching user data for telegram_id: {telegram_id}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error while fetching user data for telegram_id: {telegram_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while fetching user data for telegram_id: {telegram_id}: {e}")
            return None

    def format_subscription_status(self, user_data: Dict[str, Any]) -> str:
        try:
            username = user_data.get('username', 'Н/Д')
            status = user_data.get('status', 'UNKNOWN')

            # Format basic info
            status_text = f"Пользователь: <b>{username}</b>\n"
            status_text += f"Статус: {'✅ ' + ('<b>Активна</b>' if status == 'ACTIVE' else status) if status == 'ACTIVE' else '❌ ' + ('<b>Неактивна</b>' if status == 'INACTIVE' else status)}\n"

            # Add expiry date if available
            if 'expireAt' in user_data and user_data['expireAt']:
                from datetime import datetime, timezone, timedelta
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
                    traffic_limit_gb = traffic_limit / (1024**3)
                    used_traffic = user_data.get('usedTrafficBytes', 0)
                    used_traffic_gb = used_traffic / (1024**3)
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
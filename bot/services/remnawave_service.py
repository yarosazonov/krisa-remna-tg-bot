import httpx
from typing import Optional, Dict, Any
from config.logging_config import get_logger
from datetime import datetime, timedelta, timezone

from db.db_setup import add_user, revoke_trial

logger = get_logger(__name__)


class RemnawaveService:
    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }

    async def _get_user_by_telegram_id(self, tg_id: int) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.api_url}/api/users/by-telegram-id/{tg_id}"
                logger.info(f"Fetching user data for tg_id: {tg_id}")

                response = await client.get(url, headers=self.headers, timeout=10.0)

                if response.status_code == 200:
                    # Parsing the response body as JSON and return the result as a native Python object
                    response_data = response.json()

                    # API returns {"response": [user_data]} format
                    if 'response' in response_data and response_data['response']:
                        user_data = response_data['response'][0]  # Get first user from array
                        logger.info(f"Successfully fetched user data for tg_id: {tg_id}")
                        return user_data
                    else:
                        logger.info(f"User not found for tg_id: {tg_id}")
                        return None
                elif response.status_code == 404:
                    logger.info(f"User not found for tg_id: {tg_id}")
                    return None
                else:
                    logger.error(f"API request failed with status {response.status_code}: {response.text}")
                    return None

        except httpx.TimeoutException:
            logger.error(f"Timeout while fetching user data for tg_id: {tg_id}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error while fetching user data for tg_id: {tg_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while fetching user data for tg_id: {tg_id}: {e}")
            return None

    def _format_subscription_status(self, user_data: Dict[str, Any]) -> str:
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
        


    async def get_formatted_status(self, tg_id: int) -> str:
        user_data = await self._get_user_by_telegram_id(tg_id)
        if not user_data:
            return None
        return self._format_subscription_status(user_data)



    # Synchronizes the panel with the bot db
    #
    #
    async def sync_with_panel(self):
        """
        Retrieves all users from the panel and adds the to the db, revoking the trial eligibility

        Returns: total users found, users with id
        """
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.api_url}/api/users"
                logger.info(f"Syncing with the panel")
                
                # API responce is paginated
                size = 50
                start = 0
                all_users = []
                total_users = None

                while True:
                    response = await client.get(
                        url,
                        headers=self.headers,
                        params={"size": size, "start": start},
                        timeout=10.0
                    )

                    if response.status_code != 200:
                        logger.error(f"API request failed with status {response.status_code}: {response.text}")
                        return None

                    # API returns {"response": {users: [user_data_0], [user_data_1]}} format
                    response_data = response.json()
                    users = response_data.get("response", {}).get("users", [])
                    total_users = response_data.get("response", {}).get("total", len(users))

                    if not users:
                        break

                    all_users.extend(users)
                    start += size

                    # stop if we've already collected everything
                    if len(all_users) >= total_users:
                        break


                if not users:
                    logger.info(f"No users found")
                    return None
                
                logger.info(f"Total users reported by API: {total_users}")
                logger.info(f"Users fetched: {len(all_users)}")

                
                users_with_tg_id = 0
                for user in all_users:
                    tg_id = user.get("telegramId")

                    if tg_id:
                        users_with_tg_id += 1
                        try:
                            await add_user(tg_id)
                            await revoke_trial(tg_id)
                        except Exception as e:
                            logger.error(f"Failed to process tg_id={tg_id}: {e}")
                    else:
                        logger.info(f"No telegramId for user: {user.get('username')}")

                return total_users, users_with_tg_id
                
        except httpx.TimeoutException:
            logger.error(f"Timeout while fetching users")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error while fetching users: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while fetching users: {e}")
            return None



    # Grants a user a trial
    #
    #
    async def grant_trial(self, tg_id: int, tg_tag: str, trial_days: int, trial_traffic: int, internal_squads: str):
        """
        Creates a new trial user associated with a Telegram ID
        Args:
            tg_id,
            tg_tag,
            trial_days,
            trial_traffic,
            internal_squads
        
        Returns:
            dict | None: JSON response from the API or None if failed
        """
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.api_url}/api/users"

                expire_at = (datetime.now(timezone.utc) + timedelta(days=trial_days)).isoformat().replace("+00:00", "Z")
                username = f"{tg_tag}_{tg_id}"
                trafficLimitBytes = trial_traffic * 1024**3
                squads = [s.strip() for s in internal_squads.split(",") if s.strip()]

                payload = {
                    "telegramId": tg_id,
                    "username": username,
                    "status": "ACTIVE",
                    "expireAt": expire_at,
                    "trafficLimitBytes": trafficLimitBytes,
                    "activeInternalSquads": squads
                }

                logger.info(f"Granting a trial to a user with id: {tg_id}")

                response = await client.post(url, headers=self.headers, json=payload, timeout=10.0)

                if response.status_code == 201:
                    data = response.json()
                    logger.info(f"Trial user created: {data}")
                    return data
                else:
                    logger.error(f"API request failed [{response.status_code}]: {response.text}")
                    return None

        except httpx.TimeoutException:
            logger.error(f"Timeout while creating trial user for tg_id: {tg_id}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error while creating trial user for tg_id: {tg_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while creating trial user for tg_id: {tg_id}: {e}")
            return None

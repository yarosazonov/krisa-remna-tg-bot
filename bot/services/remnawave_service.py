import hashlib
import hmac
import json
import httpx
from typing import Optional, Dict, Any
from config.logging_config import get_logger
from datetime import datetime, timedelta, timezone

from config.settings import get_settings
from helpers.helpers import bytes_to_gb, gb_to_bytes
from db.db_setup import add_user, revoke_trial

logger = get_logger(__name__)
settings = get_settings()

# Timeout for httpx requests
TIMEOUT_SECONDS = 10.0

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

                response = await client.get(url, headers=self.headers, timeout=TIMEOUT_SECONDS)

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
        

    # User creating internal method
    #
    #
    async def _create_user(self, tg_id: int, tg_tag: str, subscription_days: int, traffic: int, internal_squads: str, trafficLimitStrategy: str = "MONTH"):
        """
        Creates a new user associated with a Telegram ID
        Args:
            tg_id,
            tg_tag,
            subscription_days,
            traffic,
            internal_squads,
            trafficLimitStrategy: str = "MONTH"
        
        Returns:
            dict | None: JSON response from the API or None if failed
        """
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.api_url}/api/users"

                expire_at = (datetime.now(timezone.utc) + timedelta(days=subscription_days)).isoformat().replace("+00:00", "Z")
                username = f"{tg_tag}_{tg_id}"
                trafficLimitBytes = gb_to_bytes(traffic)
                squads = [s.strip() for s in internal_squads.split(",") if s.strip()]

                payload = {
                    "telegramId": tg_id,
                    "username": username,
                    "status": "ACTIVE",
                    "expireAt": expire_at,
                    "trafficLimitBytes": trafficLimitBytes,
                    "activeInternalSquads": squads,
                    "trafficLimitStrategy": trafficLimitStrategy
                }

                logger.info(f"Creating a new user with id: {tg_id}")

                response = await client.post(url, headers=self.headers, json=payload, timeout=TIMEOUT_SECONDS)

                if response.status_code == 201:
                    data = response.json()
                    logger.info(f"User created: {data}")
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


    # User update internal method
    #
    #
    async def _update_user(
        self,
        uuid: str,
        activeInternalSquads: Optional[list[str]] = None,
        description: Optional[str] = None,
        email: Optional[str] = None,
        expireAt: Optional[datetime] = None,
        hwidDeviceLimit: Optional[int] = None,
        status: Optional[str] = None,  # must be "ACTIVE" or "DISABLED"
        tag: Optional[str] = None,     # max length 16, pattern ^[A-Z0-9_]+$
        telegramId: Optional[int] = None,
        trafficLimitBytes: Optional[int] = None,
        trafficLimitStrategy: str = "MONTH"  # default
    ) -> Optional[Dict[str, Any]]:
        """
        Updates a user in the Remnawave panel.

        Args:
            uuid (str): User UUID (required)
            activeInternalSquads (list[str]): Internal squads to assign
            description (str | None): User description
            email (str | None): Email address
            expireAt (datetime | None): Expiration datetime (UTC)
            hwidDeviceLimit (int | None): Max device limit
            status (str | None): "ACTIVE" or "DISABLED"
            tag (str | None): User tag (max 16 chars, pattern ^[A-Z0-9_]+$)
            telegramId (int | None): Telegram ID
            trafficLimitBytes (int | None): Traffic limit in bytes (0 = unlimited)
            trafficLimitStrategy (str): Reset strategy ("NO_RESET", "DAY", "WEEK", "MONTH")

        Returns:
            dict | None: JSON response from API, or None on failure
        """
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.api_url}/api/users/"

                # Building the payload using dict comprehension
                payload: Dict[str, Any] = {
                    k: v
                    for k, v in {
                        "uuid": uuid,
                        "activeInternalSquads": activeInternalSquads,
                        "description": description,
                        "email": email,
                        "expireAt": expireAt,
                        "hwidDeviceLimit": hwidDeviceLimit,
                        "status": status,
                        "tag": tag,
                        "telegramId": telegramId,
                        "trafficLimitBytes": trafficLimitBytes,
                        "trafficLimitStrategy": trafficLimitStrategy
                    }.items()
                    if v is not None
                }

                # API requires ISO8601 format with Z
                if "expireAt" in payload:
                    payload["expireAt"] = payload["expireAt"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

                logger.info(f"Updating user {uuid} with payload: {payload}")

                response = await client.patch(url, headers=self.headers, json=payload, timeout=TIMEOUT_SECONDS)

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"User {uuid} updated successfully: {data}")
                    return data
                else:
                    logger.error(f"API request failed [{response.status_code}]: {response.text}")
                    return None

        except httpx.TimeoutException:
            logger.error(f"Timeout while updating user {uuid}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error while updating user {uuid}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while updating user {uuid}: {e}")
            return None


    async def get_formatted_status(self, tg_id: int) -> Optional[str]:
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
                        timeout=TIMEOUT_SECONDS
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
    async def grant_trial(self, tg_id: int, tg_tag: str):
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
            return await self._create_user(
                tg_id=tg_id, 
                tg_tag=tg_tag, 
                subscription_days=settings.TRIAL_DAYS, 
                traffic=settings.TRIAL_TRAFFIC_GB, 
                internal_squads=settings.SQUADS
                )
        
        except Exception as e:
            logger.error(f"Unexpected error while creating trial user for tg_id: {tg_id}: {e}")
            return None



    # Handles the successful payment
    #
    #
    async def handle_payment(
        self,
        tg_id: int,
        tg_tag: str,
        subscription_days: int
    ) -> Optional[Dict[str, Any]]:
        """
        Handles user subscription payment.
        - If the user does not exist in the panel, they are created.
        - If the user exists, their expiry time is extended.

        Args:
            tg_id (int): Telegram user ID
            tg_tag (str): Telegram username/tag
            subscription_days (int): Number of days to add
            traffic (int): Traffic limit in GB
            internal_squads (str): Comma-separated squads

        Returns:
            dict | None: API response (created/updated user) or None on failure
        """
        try:
            # Step 1: Try to fetch user by tg_id
            user_data = await self._get_user_by_telegram_id(tg_id)

            if not user_data:
                # Step 2: If not found → create new user
                logger.info(f"User {tg_id} not found in panel, creating a new one...")
                return await self._create_user(
                    tg_id=tg_id,
                    tg_tag=tg_tag,
                    subscription_days=subscription_days,
                    traffic=settings.MONTHLY_TRAFFIC_GB,
                    internal_squads=settings.SQUADS
                )

            # Step 3: If found → extend subscription
            logger.info(f"User {tg_id} found in panel, extending subscription...")

            uuid = user_data.get("uuid")
            if not uuid:
                logger.error(f"Cannot update user {tg_id} — missing UUID in API response")
                return None

            # Parse current expiration date (if any)
            now_utc = datetime.now(timezone.utc)
            expire_at_str = user_data.get("expireAt")
            if expire_at_str:
                try:
                    expire_at = datetime.fromisoformat(expire_at_str.replace("Z", "+00:00"))
                except ValueError:
                    logger.error(f"Invalid expireAt format for user {tg_id}: {expire_at_str}")
                    expire_at = now_utc
            else:
                expire_at = now_utc

            # If subscription is still active, add on top; otherwise, start fresh
            if expire_at > now_utc:
                new_expire_at = expire_at + timedelta(days=subscription_days)
            else:
                new_expire_at = now_utc + timedelta(days=subscription_days)

            return await self._update_user(
                uuid=uuid,
                expireAt=new_expire_at,
                status="ACTIVE"
            )

        except Exception as e:
            logger.error(f"Unexpected error while handling payment for tg_id={tg_id}: {e}")
            return None



    # Validates panel webhook
    #
    #
    def validate_webhook(self, body, signature, webhook_secret_header):
        """Validate webhook signature"""
        logger.warning("Remna webhook validation started")
        
        if isinstance(body, bytes):
            body = body.decode("utf-8")

        if isinstance(body, str):
            original_body = body
            logger.warning("Body is string, parsing for logging...")
            try:
                parsed_body = json.loads(body)
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse body: %s", e)
                return False
        else:
            original_body = json.dumps(body, separators=(',', ':'))
            parsed_body = body

        computed_signature = hmac.new(
            webhook_secret_header.encode('utf-8'),
            original_body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        logger.warning("Remna webhook validated")
        return hmac.compare_digest(computed_signature, signature)

import hashlib
import hmac
import json
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from config import get_logger, get_settings
from helpers import bytes_to_gb, gb_to_bytes, format_subscription_status
from db import add_user, revoke_trial

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
 

    # =============================
    # Getting a user from the panel
    # =============================
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

    # =============================
    # User creating internal method
    # =============================
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

    # ===========================
    # User update internal method
    # ===========================
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
                url = f"{self.api_url}/api/users"

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

    # =======================================
    # Outputs the formatted data about a user
    # =======================================
    async def get_formatted_status(self, tg_id: int) -> Optional[str]:
        user_data = await self._get_user_by_telegram_id(tg_id)
        if not user_data:
            return None
        return format_subscription_status(user_data)

    # ======================================
    # Synchronizes the panel with the bot db
    # ======================================
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


                if not all_users:
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

    # =====================
    # Grants a user a trial
    # =====================
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

    # ==============================
    # Handles the successful payment
    # ==============================
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
                trafficLimitBytes=gb_to_bytes(settings.MONTHLY_TRAFFIC_GB),
                status="ACTIVE"
            )

        except Exception as e:
            logger.error(f"Unexpected error while handling payment for tg_id={tg_id}: {e}")
            return None

    # =======================
    # Validates panel webhook
    # =======================
    def validate_webhook(self, body, signature, webhook_secret_header):
        """Validate webhook signature"""
        logger.info("Remna webhook validation started")
        
        if isinstance(body, bytes):
            body = body.decode("utf-8")

        if isinstance(body, str):
            original_body = body
            logger.info("Body is string, parsing for logging...")
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
        logger.info("Remna webhook validated")
        return hmac.compare_digest(computed_signature, signature)

    # =========================
    # Updates subscription link
    # =========================
    async def update_subscription(self, telegram_id: int):
        user_info = await self._get_user_by_telegram_id(tg_id=telegram_id)
        if not user_info:
            logger.warning(f"Cannot revoke subscription: User {telegram_id} not found.")
            return None

        uuid = user_info.get("uuid")
        
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.api_url}/api/users/{uuid}/actions/revoke"

                response = await client.post(url, headers=self.headers, timeout=TIMEOUT_SECONDS)

                if response.status_code == 200:
                    logger.info(f"Successfully revoked user's subscription with tg_id: {telegram_id}")

                elif response.status_code == 404:
                    logger.info(f"Wasn't able to revoke the subscription, user not found for tg_id: {telegram_id}")
                    return None
                else:
                    logger.error(f"Revoking subscription API request failed with status {response.status_code}: {response.text}")
                    return None
            
        except httpx.TimeoutException:
            logger.error(f"Timeout while fetching user data for tg_id: {telegram_id}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error while fetching user data for tg_id: {telegram_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while fetching user data for tg_id: {telegram_id}: {e}")
            return None
from pathlib import Path
from sqlalchemy import Column, Integer, Boolean, ForeignKey, String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, selectinload
from sqlalchemy.future import select
from sqlalchemy import update
from typing import Any, List, Dict
import aiosqlite # do not delete, is needed for DATABASE_URL creation and for pipreqs to add it into requirements.txt

from config.logging_config import get_logger

logger = get_logger(__name__)

# .db is created in the __file__ folder
BASE_DIR = Path(__file__).resolve().parent
DB_NAME = 'bot.db'
DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR}/{DB_NAME}"

# Creating the engine 
engine = create_async_engine(DATABASE_URL, echo=True)
# Wrapping the engine with a sessionmaker
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

# Creating a Base class from which my Classes will inherit
Base = declarative_base()

# This class inherits from the Base class
class User(Base):
    # Each instance of the class "User" is a row in a "users" databas
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)  # auto-increment internal id
    telegram_id = Column(Integer, unique=True, nullable=False)
    eligible_for_trial = Column(Boolean, default=True)
    referrer_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=True)
    balance = Column(Integer, default=0)
    ref_cashback_percentage = Column(Integer, default=10)
    telegram_username = Column(String, index=True)

    # Self-referencing relationship
    referrer = relationship(
        "User",
        # when calling the referrer attribute remote_side defines parent/child relationship between referrer_id and telegram_id. Remote side is parent.
        remote_side=[telegram_id],
        # This creates the reverse relation, retrieves the list of Users whose referrer_id is equal to this user’s telegram_id    
        backref="referees"  
    )

async def init_db():
    try:
        logger.info('Initializing database...')
        async with engine.begin() as conn:
            # Base.metadata keeps all table definitions so you can create tables in the database with Base.metadata.create_all(engine)
            await conn.run_sync(Base.metadata.create_all)
        logger.info('Database initialized successfully.')
    except Exception as e:
        logger.error(f'Error during db initialization: {e}')




# Adding a user to the db
#
#
async def add_user(telegram_id: int, referrer_id: int | None = None, telegram_username: str | None = None):
    async with async_session() as session:
        async with session.begin():
            logger.info(f'Trying to add user with telegram_id={telegram_id}')
            # Check if user exists
            # session.execute() returns a Result object, even if no matches found
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            # Returns User object or None
            existing_user = result.scalar_one_or_none()
            if existing_user:
                logger.info(f'User with telegram_id={telegram_id} already exists.')
                return existing_user

            user = User(
                telegram_id=telegram_id,
                referrer_id=referrer_id,
                telegram_username=telegram_username
            )
            session.add(user)
            logger.info(f'User with telegram_id={telegram_id} added to session.')
        await session.commit()
        logger.info(f'User with telegram_id={telegram_id} committed to database.')
        return user
    


# Getting a user
#
#
async def get_user(telegram_id: int) -> User: 
    async with async_session() as session:
        logger.info(f'Fetching user with telegram_id={telegram_id}')
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            logger.info(f'User found: telegram_id={telegram_id}')
        else:
            logger.info(f'No user found with telegram_id={telegram_id}')
        return user



# Updating a user
#
#
async def update_user(
    telegram_id: int,
    eligible_for_trial: bool | None = None,
    referrer_id: int | None = None,
    balance_increment: int | None = None,
    ref_cashback_percentage: int | None = None,
    telegram_username: str | None = None
) -> User:
    """
    Update fields of a user identified by telegram_id.
    Example:
        await update_user(
            12345,
            balance=100,
            eligible_for_trial=False,
            telegram_username="hero123"
        )
    """
    async with async_session() as session:
        async with session.begin():
            values_to_update: Dict[str, Any] = {
                k: v
                for k, v in {
                    "eligible_for_trial": eligible_for_trial,
                    "referrer_id": referrer_id,
                    "ref_cashback_percentage": ref_cashback_percentage,
                    "telegram_username": telegram_username
                }.items() 
                if v is not None
            }

            if not values_to_update and balance_increment is None:
                logger.warning(f"No fields provided to update for user {telegram_id}")
                return None

            if balance_increment is not None:
                values_to_update["balance"] = User.balance + balance_increment

            stmt = update(User).where(User.telegram_id == telegram_id).values(**values_to_update)
            
            logger.info(f"Updating user {telegram_id} with values: {values_to_update} and balance_increment: {balance_increment}")
            await session.execute(stmt)
            stmt = select(User).where(User.telegram_id == telegram_id)
            updated_user = await session.scalar(stmt)

        logger.info(f"User {telegram_id} updated successfully.")

        return updated_user




# Revoking a trial
#
#
async def revoke_trial(telegram_id: int):
    """
    Revoke the trial eligibility of a specific user.
    Sets eligible_for_trial = False for the user with the given telegram_id.
    """
    async with async_session() as session:
        async with session.begin():
            logger.info(f'Revoking trial for user with telegram_id={telegram_id}')
            # Update eligible_for_trial to False
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(eligible_for_trial=False)
            )
        await session.commit()
        logger.info(f'Trial revoked for user with telegram_id={telegram_id}')



# Getting all referees
#
#
async def get_referees(telegram_id: int) -> List:
    """
    Outputs a list of users referred by the user with the given telegram_id,
    using the backref relationship.
    """
    async with async_session() as session:
        async with session.begin():
            logger.warning(f'Looking for the referred users for telegram_id: {telegram_id}')
            result = await session.execute(
                select(User)
                .options(selectinload(User.referees))
                .where(User.telegram_id == telegram_id))
            
            user = result.scalar_one_or_none()

            if not user or not user.referees:
                return {}

            # Access the backref relationship
            referees_dict = {r.telegram_id: r.telegram_username for r in user.referees}
            logger.warning(f'User {telegram_id} has referees: {referees_dict}')
            return referees_dict
        



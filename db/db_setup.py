from pathlib import Path
from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.future import select
from sqlalchemy import update
import aiosqlite

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

    id = Column(Integer, primary_key=True, index=True)  # auto-increment internal id
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    eligible_for_trial = Column(Boolean, default=True)
    referrer_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=True)

    # Self-referencing relationship
    referrer = relationship(
        "User",
        remote_side=[telegram_id],
        backref="referees"  # This creates the reverse relation
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
async def add_user(telegram_id: int, referrer_id: int | None = None):
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
                referrer_id=referrer_id
            )
            session.add(user)
            logger.info(f'User with telegram_id={telegram_id} added to session.')
        await session.commit()
        logger.info(f'User with telegram_id={telegram_id} committed to database.')
        return user
    


# Getting a user
async def get_user(telegram_id: int):
    async with async_session() as session:
        logger.info(f'Fetching user with telegram_id={telegram_id}')
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            logger.info(f'User found: telegram_id={telegram_id}')
        else:
            logger.info(f'No user found with telegram_id={telegram_id}')
        return user


# Revoking a trial
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
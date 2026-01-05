import subprocess
from datetime import datetime
from pathlib import Path
import sqlite3
import sys
import shutil
sys.path.append(str(Path(__file__).resolve().parents[1]))
import logging
from aiogram import Bot
from bot.services.notification_service import send_backup_to_admin
import asyncio

from config.logging_config import get_logger, setup_logging
from config.settings import get_settings


if not logging.getLogger().hasHandlers():
    setup_logging()

logger = get_logger(__name__)
settings = get_settings()

DATE = datetime.now().strftime("%d-%m-%y")
ROOT_DIR = Path(__file__).resolve().parents[1]
BACKUPS_DIR = ROOT_DIR / 'backups' / f'{DATE}'
BACKUPS_DIR.mkdir(exist_ok=True)
SQLITE_DIR = ROOT_DIR / 'db'


def backup_postgress():
    """Generates a postgres dump"""

    backup_file = BACKUPS_DIR / f"postgres-backup-{DATE}.dump"
    cmd = ['docker', 'exec', '-i', 'remnawave-db', 'pg_dump', '-U', 'postgres', '-d', 'postgres', '-Fc']
    try:
        with open(backup_file, "wb") as f:
            subprocess.run(cmd, stdout=f, check=True)

        logger.info("Postgress dump successful")
    except subprocess.CalledProcessError as e:
        logger.error(f"Postgres dump failed: {e}")
        return
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return

def backup_sqlite():
    """Generates a sqlite dump"""

    db_path = SQLITE_DIR / 'bot.db'
    backup_file = BACKUPS_DIR / f'sqlite-backup-{DATE}.db'

    try:
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(backup_file)
        with src, dst:
            src.backup(dst)
        src.close()
        dst.close()

        logger.info("Sqlite dump successful")
    except Exception as e:
        logger.error(f"Sqlite dump failed: {e}")

def create_encrypted_archive() -> str:
    """
        Archives and encrypts a backup folder
    
    Returns:
        str: The path to the encrypted archive
    """
    
    # Create the archive in the backups root directory
    archive_path = BACKUPS_DIR.parent / f'{DATE}.tar.gz'
    encrypted_path = BACKUPS_DIR.parent / f'{DATE}.tar.gz.gpg'
    
    # -C changes to the parent dir, so we just tar the folder name "04-01-26"
    # This prevents storing the full absolute path in the archive
    tar_cmd = [
        'tar', 
        '-czf', 
        archive_path, 
        '-C', BACKUPS_DIR.parent, 
        BACKUPS_DIR.name
    ]
    
    # 2. Encrypt using GPG
    gpg_cmd = [
        'gpg', 
        '--batch', 
        '--yes', 
        '--passphrase', settings.BACKUP_PASSWORD, 
        '--cipher-algo', 'AES256', 
        '-c', 
        '-o', encrypted_path, 
        archive_path
    ]

    try:
        # Create .tar.gz
        subprocess.run(tar_cmd, check=True)
        
        # Encrypt to .gpg
        subprocess.run(gpg_cmd, check=True)
        
        # Cleanup unencrypted archive and raw directory
        archive_path.unlink()   
        shutil.rmtree(BACKUPS_DIR)
        
        logger.info(f"Encrypted archive created: {encrypted_path.name}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Tar failed: {e}")
        return
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return

    return str(encrypted_path)


async def main():
    backup_postgress()    
    backup_sqlite()
    archive_path = create_encrypted_archive()
    
    if archive_path:
        async with Bot(token=settings.BOT_TOKEN).context() as bot:
            await send_backup_to_admin(bot, archive_path)

if __name__ == "__main__":
    asyncio.run(main())

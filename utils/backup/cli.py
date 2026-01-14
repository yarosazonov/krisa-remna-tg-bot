"""CLI entry point for backup and restore operations."""

import argparse
import asyncio
import shutil
import sys
from datetime import datetime
from pathlib import Path

from aiogram import Bot

from config.logging_config import get_logger, setup_logging
from config.settings import get_settings

from .archive import create_encrypted_archive, decrypt_archive
from .postgres import backup_postgres, restore_postgres
from .sqlite import backup_sqlite, restore_sqlite

setup_logging()
logger = get_logger(__name__)
settings = get_settings()

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKUPS_ROOT = ROOT_DIR / 'backups'
SQLITE_DB_PATH = ROOT_DIR / 'db' / 'bot.db'


def _get_notification_service():
    from bot.services.notification_service import send_backup_to_admin
    return send_backup_to_admin


async def run_backup() -> Path | None:
    """Performs a full backup and sends it to admin."""
    
    date_str = datetime.now().strftime("%d-%m-%y")
    backup_dir = BACKUPS_ROOT / date_str
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    backup_postgres(backup_dir, date_str)
    backup_sqlite(SQLITE_DB_PATH, backup_dir, date_str)
    
    archive_path = create_encrypted_archive(backup_dir, settings.BACKUP_PASSWORD)
    
    if archive_path:
        send_backup_to_admin = _get_notification_service()
        async with Bot(token=settings.BOT_TOKEN).context() as bot:
            await send_backup_to_admin(bot, str(archive_path))
    
    return archive_path


def run_restore(
    encrypted_path: str,
    postgres_only: bool = False,
    sqlite_only: bool = False
) -> bool:
    """Restores databases from an encrypted backup."""

    logger.info(f"Starting restore from: {encrypted_path}")
    
    try:
        backup_dir = decrypt_archive(Path(encrypted_path), settings.BACKUP_PASSWORD)
        logger.info(f"Backup extracted to: {backup_dir}")
        
        success = True
        
        if not sqlite_only:
            if not restore_postgres(backup_dir):
                success = False
        
        if not postgres_only:
            if not restore_sqlite(backup_dir, SQLITE_DB_PATH):
                success = False
        
        # Cleanup
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
            logger.info("Cleaned up extracted backup directory")
        
        return success
        
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Backup and restore utility for PostgreSQL and SQLite databases'
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    subparsers.add_parser('backup', help='Create a backup and send to admin')
    
    restore_parser = subparsers.add_parser('restore', help='Restore from a backup file')
    restore_parser.add_argument('backup_file', help='Path to the encrypted .gpg backup file')
    restore_parser.add_argument('--postgres-only', action='store_true', help='Only restore PostgreSQL')
    restore_parser.add_argument('--sqlite-only', action='store_true', help='Only restore SQLite')
    
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    
    if args.command == 'backup' or args.command is None:
        await run_backup()
    elif args.command == 'restore':
        success = run_restore(
            args.backup_file,
            postgres_only=args.postgres_only,
            sqlite_only=args.sqlite_only
        )
        if not success:
            sys.exit(1)
    else:
        print("Use 'backup' or 'restore' command. Run with --help for more info.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

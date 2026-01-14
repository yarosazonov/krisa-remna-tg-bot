"""SQLite backup and restore functions."""

import shutil
import sqlite3
from pathlib import Path

from config.logging_config import get_logger

logger = get_logger(__name__)


def backup_sqlite(db_path: Path, backup_dir: Path, date_str: str) -> Path | None:
    """Generates SQLite db backup"""
    
    backup_file = backup_dir / f'sqlite-backup-{date_str}.db'
    
    try:
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(backup_file)
        with src, dst:
            src.backup(dst)
        src.close()
        dst.close()
        
        logger.info("SQLite dump successful")
        return backup_file
    except Exception as e:
        logger.error(f"SQLite dump failed: {e}")
        return None


def restore_sqlite(backup_dir: Path, target_path: Path) -> bool:
    """Restores SQLite database from a backup file."""
    
    sqlite_files = list(backup_dir.glob("sqlite-backup-*.db"))
    
    if not sqlite_files:
        logger.error(f"No SQLite backup file found in {backup_dir}")
        return False
    
    backup_file = sqlite_files[0]
    logger.info(f"Restoring SQLite from: {backup_file.name}")
    
    try:
        # Create a safety backup before overwriting
        if target_path.exists():
            temp_backup = target_path.with_suffix('.db.pre-restore')
            shutil.copy2(target_path, temp_backup)
            logger.info(f"Created pre-restore backup: {temp_backup.name}")
        
        shutil.copy2(backup_file, target_path)
        
        # Verify the restored database
        conn = sqlite3.connect(target_path)
        conn.execute("SELECT 1")
        conn.close()
        
        logger.info("SQLite restore successful")
        return True
        
    except Exception as e:
        logger.error(f"SQLite restore failed: {e}")
        pre_restore = target_path.with_suffix('.db.pre-restore')
        if pre_restore.exists():
            shutil.copy2(pre_restore, target_path)
            logger.info("Restored original database from pre-restore backup")
        return False

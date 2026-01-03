import subprocess
from datetime import datetime
from pathlib import Path
import sqlite3
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
import logging

from config.logging_config import get_logger, setup_logging



if not logging.getLogger().hasHandlers():
    setup_logging()

logger = get_logger(__name__)

DATE = datetime.now().strftime("%d-%m-%y")
ROOT_DIR = Path(__file__).resolve().parents[1]
BACKUPS_DIR = ROOT_DIR / 'backups'
BACKUPS_DIR.mkdir(exist_ok=True)
SQLITE_DIR = ROOT_DIR / 'db'


def postgress_dump():
    """Generates a postgres dump"""

    backup_file = BACKUPS_DIR / f"postgres-backup-{DATE}.dump"
    cmd = ['docker', 'exec', '-i', 'remnawave-db', 'pg_dump', '-U', 'postgres', '-d', 'postgres', '-Fc']
    try:
        with open(backup_file, "wb") as f:
            subprocess.run(cmd, stdout=f, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Postgres dump failed: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


def sqlite_dump():
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
    except Exception as e:
        logger.error(f"Sqlite dump failed: {e}")



def main():
    postgress_dump()    
    sqlite_dump()


if __name__ == "__main__":
    main()

# 1. execute pg_dump on the postgres container and store the .dump in the backups folder
# 2. define the way to achieve the same result for sqlite (dump like utility or just copy the db?)
# 3. Archive both files and encrypt them (or just set archive pass)
# 4. Send the archive to the admin usind ADMIN_ID in .env
# Setup a cron job to automate the script execution
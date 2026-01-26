import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1] 

LOG_FILE_SIZE_MB = 5

def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the application."""

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    log_dir = BASE_DIR / 'data' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'bot.log'
    
    from helpers import mb_to_bytes

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=[
            # Commented out this line to prevent logs from printing in the terminal
            # logging.StreamHandler(sys.stdout),
            RotatingFileHandler(
                log_file, 
                maxBytes=mb_to_bytes(LOG_FILE_SIZE_MB),  # 5 MB
                backupCount=5,          # Keep 5 backup files
                encoding="utf-8"
            )
        ]
    )

    # Set specific loggers
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)



def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
import logging
import sys
from pathlib import Path

def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the application."""

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    log_dir = Path('logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'bot.log'

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=[
            # Commented out this line to prevent logs from printing in the terminal
            # logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8")
        ]
    )

    # Set specific loggers
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
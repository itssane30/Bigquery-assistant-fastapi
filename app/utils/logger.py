"""
app/utils/logger.py
---------------------
One shared logger setup used across the whole app: console + rotating
file at backend/logs/application.log.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(_BACKEND_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

_FORMATTER = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:  # already configured - avoid duplicate handlers on reimport
        return logger

    logger.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(_FORMATTER)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "application.log"), maxBytes=5_000_000, backupCount=3
    )
    file_handler.setFormatter(_FORMATTER)
    logger.addHandler(file_handler)

    return logger

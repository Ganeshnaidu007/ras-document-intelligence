"""utils/logger.py — Centralised logging configuration."""
import logging, os

LOG_LEVEL = os.getenv("RAS_LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

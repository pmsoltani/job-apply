import logging
import logging.handlers
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_FORMAT = "{asctime} | {name} | {levelname:<8} | {filename:<16} | {message}"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def logger_factory(
    name: str,
    log_file: Path,
    *,
    logger_level: int = logging.DEBUG,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 5,
) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:  # Avoid adding duplicate handlers
        return logger

    logger.setLevel(logger_level)
    logger.propagate = False  # Prevent duplicate logs from root logger
    log_file.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(fmt=LOG_FORMAT, style="{", datefmt=DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        filename=log_file,
        mode="a",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

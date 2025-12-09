"""Настройка логирования для проекта."""

import logging
import sys


def setup_logger(name: str = "ai_browser_agent", level: int = logging.INFO) -> logging.Logger:
    """
    Настраивает и возвращает логгер.

    Args:
        name: Имя логгера.
        level: Уровень логирования.

    Returns:
        Настроенный логгер.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Удаляем существующие обработчики
    logger.handlers.clear()

    # Создаем форматтер
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

"""
Инициализация логирования.
"""

import logging
import os
import sys

from constants import BASE_DIR

try:
    from colorama import Fore, Style, init

    init(autoreset=True)
    COLORAMA_INSTALLED = True
except ImportError:
    COLORAMA_INSTALLED = False
    class EmptyColor:
        def __getattr__(self, name): return ""
    Fore = Style = EmptyColor()


class ColoredFormatter(logging.Formatter):
    """Кастомный форматировщик с выровненными и цветными уровнями логов."""

    # Шаблон: время | уровень (выровнен) | модуль (выровнен до 8 симв.) : сообщение
    log_fmt = f"{Fore.WHITE}%(asctime)s{Style.RESET_ALL} %(levelname_colored)s {Fore.BLUE}%(filename)-8s{Style.RESET_ALL}: %(message)s"

    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, Fore.WHITE)
        # Выравниваем уровень лога внутри квадратных скобок до 5 символов [INFO ], [ERROR]
        levelname_padded = f"[{record.levelname:<5}]"
        record.levelname_colored = f"{color}{levelname_padded}{Style.RESET_ALL}"

        formatter = logging.Formatter(self.log_fmt, datefmt=self.datefmt)
        return formatter.format(record)


def setup_logging(level: int | str = logging.INFO,use_colors: bool = True,log_to_file: bool = True) -> None:
    """
    Настраивает корневой логгер для всего проекта.

    Args:
        level: Порог логирования (по умолчанию INFO).
        use_colors: Если True и colorama установлена — вывод в консоль будет цветным.
        log_to_file: Если True, параллельно пишет логи в файл.
    """
    # Приоритет уровня: по умолчанию < аргумент < переменная окружения
    env_level = os.environ.get("LOG_LEVEL")
    if env_level:
        try:
            level = int(env_level) if env_level.isdigit() else getattr(logging, env_level.upper())
        except (AttributeError, ValueError):
            pass

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()  # Очищаем старые обработчики

    # 1. ОБРАБОТЧИК ДЛЯ КОНСОЛИ (sys.stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if use_colors and COLORAMA_INSTALLED:
        console_formatter = ColoredFormatter(datefmt="%H:%M:%S")
    else:
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)-5s] %(filename)-8s: %(message)s",
            datefmt="%H:%M:%S",
        )

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 2. ОБРАБОТЧИК ДЛЯ ФАЙЛА (script_logs.txt)
    if log_to_file:
        log_file_path = BASE_DIR/"script_logs.txt"

        file_handler = logging.FileHandler(log_file_path, mode="a", encoding="utf-8")
        file_handler.setLevel(level)

        if log_file_path.is_file() and log_file_path.stat().st_size > 0:
            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write("\n\n" + "=" * 60 + "\n   ЗАПУСК НОВОЙ СЕССИИ\n" + "=" * 60 + "\n\n")
                #todo изменить разделение

        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)-5s] %(filename)-8s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
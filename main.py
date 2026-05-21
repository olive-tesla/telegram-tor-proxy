"""
Входная точка скрипта. Определяет дальнейший сценарий исполнения.
Занимается лишь проверкой конфигурации - ОС, Docker, и прочее. (для выбора сценария работы)
Если всё в порядке - вызывает logic.main(), который отвечает за дальнейшую работу тор-прокси

--- Вся проверка состояния в скрипте завязана на config.json: скрипт НЕ УВИДИТ, если проблемы, с другими файлами.---

Сейчас используются фиксировано те мосты, которые указаны в файле BRIDGES.txt на момент запуска скрипта
В НЕГО НУЖНО ДОБАВИТЬ МОСТЫ ВРУЧНУЮ !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

Читайте README.md - там инструкция, где брать мосты и как их добавить.
"""
import logging
import sys
from importlib.util import find_spec
from pathlib import Path

import start
from utils.file_manager import get_bridges_from_file, create_torrc
from utils.logger import setup_logging
from utils.env import is_running_in_docker, ensure_venv, install_dependencies



def main():
    # 0. флаг готовности к запуску прокси
    ready = False

    # 1. запускаем логгер (log_to_file=True,
    setup_logging(level="INFO", use_colors=True, log_to_file=False)
    logger = logging.getLogger(__name__)

    # 2. создание и перезапуск из-под .venv (игнорируем если в контейнере, бессмысленно)
    is_docker = is_running_in_docker()
    if not is_docker:
        venv_dir = Path(__file__).resolve().parent / ".venv"
        ensure_venv(venv_dir)

    # 3. устанавливаем зависимости (пропускаем, если установлено)
    if find_spec("colorama") is None:
        if not install_dependencies():
            logger.critical("Не удалось установить зависимости. Выход.")
            sys.exit(1)

    # Импортируем logic после проверки окружения (.venv, зависимости и тд)
    from core import logic

    # 4. Выбор сценария запуска (штатный - в else блоке).
    if isinstance(status := logic.load_config(), Exception):
        # Проваливаемся внутрь только при ошибке с config.json (нормально при первом запуске, т.к конфиг ещё не создан)

        if isinstance(status, FileNotFoundError):  # Сценарий первого запуска (config.json не найден)
            if start.setup():
                ready = True

        elif isinstance(status, KeyError):  # Проблема с ключами в конфиге (крайний случай, нужно разбираться вручную)
            logger.error("В конфиге нет нужного ключа\n %s\n"
                         "Попробуйте отредактировать вручную или удалить конфиг (удаление заставит скрипт произвести"
                         "'чистую' установку. Также проверьте torrc конфиг и файлы tor",status)
            #if start.setup():
            #    ready = True

    # 4.1 До-проверка docker статуса (скип если штатный запуск)
    elif is_docker != status["is_docker"]:
        logger.info(f"Способ запуска изменился: is_docker{is_docker}, прошлый запуск: is_docker{status['is_docker']}")
        if start.setup():
            ready = True

    else:  # не первый запуск, конфиги целые, всё ок.
        ready = True

    # 5. Если всё готово - берём свежие мосты и вызываем логику работы с тор-прокси
    if ready:
        #берём мосты из BRIGDES.txt если есть и всегда обновляем torrc при каждом запуске скрипта
        bridges = get_bridges_from_file()
        create_torrc(bridges)
        logic.main()


if __name__ == "__main__":
    main()
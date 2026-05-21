"""
Скрипт с логикой первого запуска и настройками работы:
- Скачивает (если не нашёл в корне) Tor Expert Bundle с офф. Сайта, используя PowerShell WebClient (на Windows)
- Распаковывает Tor архив в корень_скрипта/tor и сохраняет пути к файлам в config.json
- Создаёт в корне скрипта config.json (локальный конфиг для скрипта) и torrc ("конфиг" тора)
- Генерирует прокси в виде ссылки и автоматически пытается добавить их в Telegram (используя webbrowser)
- Устанавливает зависимости (colorama, для красоты)

- Ожидаемая структура Tor файлов:

Telegram_tor_proxy
    ├── SETUP.bat # батник для первого запуска
    ├── start_proxy.bat # батник для повседневного запуска скрипта
    ├── start.py # "Установочный" модуль для первого запуска
    ├── constants.py # константы, значения по умолчанию
    ├── core/... # ядро скрипта, основная логика для работы Tor-прокси
    ├── utils/... # вспомогательные модули для работы скрипта
    ├── torrc # Конфиг Tor
    ├── config.json # Локальный конфиг скрипта с путями к файлам и т.д (здесь можно изменить порт вручную)
    ├── README.md # инструкция
    ├─── ...
    ├── tor ── # Папка с Tor Expert Bundle (после первого запуска, распакуется сюда)
    │ ├── data ── ...
    │ ├── docs ── ...
    │ ├── tor ├── tor.exe
    │ └─...   ├───── pluggable_transports ── lyrebird.exe # Для obfs4/webtunnel/...-мостов
    └─...     ├...
"""

import sys
import venv  # noqa
import logging

from constants import TOR_EXE, TOR_DIR, ARCHIVE_PATH
from utils.download import tor_download_manager
from utils.env import is_running_in_docker
from utils.file_manager import create_config_json, create_torrc, archive_extract
from utils.logger import setup_logging
from utils.proxy import add_proxy_to_telegram, is_port_free, get_proxy_hostname, get_proxy_port

logger = logging.getLogger(__name__)


def setup() -> bool:
    logger.info("=== Настройка окружения Tor Proxy ===")

    # 1. Проверка/загрузка Tor Expert Bundle (пока его нет - не можем создать torrc, config.json)
    if not TOR_EXE.is_file():
        logger.info("Файлы Tor не найдены, начинаю установку...")
        _tor_downloaded = tor_download_manager()

        # 2. Распаковка\установка Tor Expert Bundle
        if _tor_downloaded:
            if _tor_downloaded.is_file():
                # архив найден (загружен пользователем вручную)
                logger.info("Архив с Tor (предположительно) найден по пути:\n %s", _tor_downloaded)
                archive_extract(file_path=_tor_downloaded, extract_to=TOR_DIR)
            else:
                # Тор был успешно загружен скриптом
                archive_extract(file_path=ARCHIVE_PATH, extract_to=TOR_DIR)
            pass
    else:
        logger.info("Tor уже присутствует, пропускаю загрузку.")

    # 3. порты
    is_port_free(host=get_proxy_hostname(), port=get_proxy_port())
    #todo изменить is_port_free

    # 4. Создание torrc (Tor конфиг)
    create_torrc()

    # 5. Сохраняем состояние в config.json (пути до файлов, порт прокси)
    create_config_json()
    logger.info(" === Настройка завершена! ===")

    # 6. Автоматическое добавление прокси в телеграм (если не в контейнере)
    is_docker = is_running_in_docker()
    if not is_docker:
        add_proxy_to_telegram()
        # 6. Принты с инструкциями для cli версии
        logger.info("Чтобы запустить тор-прокси в дальнейшем:")
        logger.info("1. Дважды кликните start_proxy.bat\n")
        logger.info(" === НЕ ЗАБУДЬТЕ ДОБАВИТЬ МОСТЫ! (BRIGDES.txt) (открыть можно блокнотом) ===")
        logger.info(" === НЕ ЗАБУДЬТЕ ДОБАВИТЬ МОСТЫ! (BRIGDES.txt) (открыть можно блокнотом) ===")
        logger.info(" === НЕ ЗАБУДЬТЕ ДОБАВИТЬ МОСТЫ! (BRIGDES.txt) (открыть можно блокнотом) ===\n")
        logger.warning(" === ВАЖНО - Ваше прокси работает ТОЛЬКО когда тор запущен и ТОЛЬКО когда он ===")
        logger.warning(" === установил соединение - Вы должны видеть Bootstrapped 100% в его выводе === .")
        logger.warning("=== Если соединение не доходит до Bootstrapped 100% - Смените мосты === ")

    return True


if __name__ == "__main__":
    try:
        setup_logging()
        setup()
    except KeyboardInterrupt:
        logger.error("[!] Прервано пользователем.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n[!] Критическая ошибка: {e}")
        sys.exit(1)

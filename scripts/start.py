"""
Скрипт с логикой первого запуска и настройками работы:
- Скачивает (если не нашёл в корне) Tor Expert Bundle с офф. Сайта, используя PowerShell WebClient (на Windows)
- Распаковывает Tor архив в корень_скрипта/tor и сохраняет пути к файлам в config.json
- Создаёт в корне скрипта config.json (локальный конфиг для скрипта) и torrc ("конфиг" тора)
- Генерирует прокси в виде ссылки и автоматически пытается добавить их в Telegram (используя webbrowser)
- Устанавливает зависимости (colorama, для красоты)

- Ожидаемая структура Tor файлов:

Telegram_tor_proxy
    ├── start_proxy.bat # Файл для быстрого запуска скрипта
    ├── scripts/start.py # "Установочный" модуль для первого запуска
    ├── core/... # ядро скрипта, основная логика для работы Tor-прокси
    ├── torrc # Конфиг Tor
    ├── config.json # Локальный конфиг скрипта с путями к файлам и т.д
    ├─── ...
    ├── tor ── # Папка с Tor Expert Bundle (распакуется сюда)
    │ ├── data ── ...
    │ ├── docs ── ...
    │ ├── tor ├── tor.exe
    │ └─...   ├───── pluggable_transports ── lyrebird.exe # Для obfs4/webtunnel/...-мостов
    └─...     ├...
"""

import sys
import venv  # noqa

from core.constants import TOR_EXE
from core.settings import IS_DOCKER
from core.utils import create_torrc, create_config_json, check_is_port_used, tor_download_manager, add_proxy_to_telegram


def setup() -> bool:
    print("=== Настройка окружения Tor Proxy ===")

    # 1. Проверка/установка Tor Expert Bundle (пока его нет - не можем создать torrc, config.json)
    if not TOR_EXE.exists():
        print("[*] Не вижу Tor в директории скрипта, начинаю загрузку...")
        tor_download_manager()
    else:
        print("[*] Tor уже присутствует, пропускаю загрузку.")

    # 2. порты
    check_is_port_used()

    # 3. Создание torrc (Tor конфиг)
    create_torrc(IS_DOCKER)

    # 4. Сохраняем состояние в config.json (пути до файлов, порт прокси)
    create_config_json()
    print(" === Настройка завершена! ===\n")

    # 5. Автоматическое добавление прокси в телеграм (если не в контейнере)
    if not IS_DOCKER:
        add_proxy_to_telegram()
        # 6. Принты с инструкциями для cli версии
        print(f"[!] Чтобы запустить тор-прокси в дальнейшем:\n   1. Дважды кликните start_proxy.bat")
        print(" === НЕ ЗАБУДЬТЕ ДОБАВИТЬ МОСТЫ! (BRIGDES.txt) (открыть можно блокнотом) ===")
        print(" === НЕ ЗАБУДЬТЕ ДОБАВИТЬ МОСТЫ! (BRIGDES.txt) (открыть можно блокнотом) ===")
        print(" === НЕ ЗАБУДЬТЕ ДОБАВИТЬ МОСТЫ! (BRIGDES.txt) (открыть можно блокнотом) ===\n")
        print(" === ВАЖНО - Ваше прокси работает ТОЛЬКО когда тор запущен и ТОЛЬКО когда он ===\n"
              " === установил соединение - Вы должны видеть Bootstrapped 100% в его выводе === .\n "
              "=== Если соединение не доходит до Bootstrapped 100% - Смените мосты === ")

    return True


if __name__ == "__main__":
    try:
        setup()
    except KeyboardInterrupt:
        print("\n[!] Прервано пользователем.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] Критическая ошибка: {e}")
        sys.exit(1)
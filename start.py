"""
Скрипт с логикой первого запуска и настройками работы:
- Скачивает (если не нашёл в корне/tor) Tor Expert Bundle с офф.сайта, используя PowerShell WebClient (на Windows)
- Распаковывает Tor архив в корень_скрипта/tor и сохраняет пути к файлам в config.json
- Создаёт в корне скрипта config.json (локальный конфиг для скрипта) и torrc ("конфиг" тора)
- Генерирует прокси в виде ссылки и автоматически пытается добавить их в Telegram (используя webbrowser)
- Устанавливает зависимости (colorama, для красоты)
- Функция check_environment() вызывается при каждом запуске скрипта.

- Ожидаемая структура Tor файлов:

Telegram_tor_proxy
    ├── start_proxy.bat # Файл для быстрого запуска скрипта
    ├── start.py # "Установочный" модуль для первого запуска
    ├── tor-proxy.py # Основной модуль, отвечает за работу Tor-прокси
    ├── torrc # Конфигурация Tor (редактируется пользователем)
    ├── config.json # Локальный конфиг скрипта с путями к файлам и т.д
    │ └── ...
    ├── tor ──├ # Папка с Tor Expert Bundle (распаковать сюда, при ручной загрузке)
    │ ├── data ── ...
    │ ├── docs ── ...
    │ ├── tor ├── tor.exe
    │ └─...   ├───── pluggable_transports ── lyrebird.exe # Для obfs4-мостов
    └─...     ├...
"""

import os
import sys
import time
import json
import tarfile
import subprocess
import webbrowser
import venv  # noqa
from pathlib import Path

# константы
BASE_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = BASE_DIR / "config.json"
TORRC_PATH = BASE_DIR / "torrc"
TOR_DIR = BASE_DIR / "tor"
DATA_DIR = TOR_DIR / "data"
TOR_EXE = TOR_DIR / "tor" / "tor.exe"
ARCHIVE_NAME = "tor_expert_bundle.tar.gz"
SOCKS_HOST = "127.0.0.1"
# порт (будет записан в config.json при первичной настройке)
SOCKS_PORT = 9090
# Измените порт в SOCKS_PORT или в config.json если нужно\занят указанный. (порт тора по умолчанию:9050)
TG_PROXY_LINK = f"tg://socks?server={SOCKS_HOST}&port={SOCKS_PORT}"


TOR_URL = (
"https://archive.torproject.org/tor-package-archive/torbrowser/15.0.9/"
"tor-expert-bundle-windows-x86_64-15.0.9.tar.gz"
)
# отсюда скрипт попытается скачать архив tor bundle, если не нашёл его в подпапке /tor


def check_environment():
    # 1. Проверяем, запущены ли мы из .venv
    is_venv = sys.prefix != sys.base_prefix

    if not is_venv:
        # Мы здесь, только если работаем не из .venv (пробуем найти и перезапуститься из-под него, если нет - создаём)

        # собираем пути (нужны для проверки наличия .venv)
        script_dir = Path(__file__).parent

        venv_dir = ".venv"
        venv_path = script_dir / venv_dir

        python_exe = os.path.join(script_dir, venv_dir, 'Scripts', 'python.exe')

        # Проверяем наличие папки .venv
        if venv_path.exists() and venv_path.is_dir():
            # 3. Перезапускаем этот же скрипт, но уже из-под .venv
            print("Использую существующее виртуальное окружение (.venv)...")
            sys.exit(subprocess.run([python_exe, sys.argv[0]]).returncode)
        else:
            print(".venv нет, создаю окружение...")
            # создаём окружение, функция из start.py
            create_environment(python_exe)
            print('Виртуальное окружение создано. Продолжу работу из него...')

            # 3. Перезапускаем этот же скрипт, но уже из-под .venv
            sys.exit(subprocess.run([python_exe, sys.argv[0]]).returncode)

    else:
        print(f"Используемый Python: {sys.executable}")
        # print(f"Запущено в окружении: {sys.prefix}")


def create_environment(python_exe):
    print("-- Создание виртуального окружения...")

    venv_dir = '.venv'
    venv.create(venv_dir, with_pip=True)
    req_file = 'requirements.txt'

    print("[*] Установка зависимостей...")
    try:
        # сначала обновляем pip
        subprocess.check_call([str(python_exe), "-m", "pip", "install", "--upgrade", "pip", "--quiet"])

        # Ставим всё из requirements.txt либо только colorama
        if os.path.exists(req_file):
            subprocess.check_call([str(python_exe), "-m", "pip" "install", "-r", req_file, "--quiet"])
        else:
            print("[*] requirements.txt не найден, ставлю только colorama...")
            subprocess.check_call([str(python_exe), "-m", "pip", "install", "colorama", "--quiet"])
    except Exception as err:
        print(f"-- Ошибка при установке зависимостей: {err}")


def tor_download_manager() -> None:
    """Управляет процессом загрузки tor expert bundle,
    метод загрузки выбирается в блоке try:
     Не загружает сам напрямую, за это отвечает другая функция"""
    TOR_DIR.mkdir(exist_ok=True)

    archive_path = BASE_DIR / ARCHIVE_NAME

    try:
        print("\n[*] Пробую скачать через PowerShell...")
        if download_with_pwsh(TOR_URL, archive_path):
            print("\n[!] Загрузка прошла успешно!")
        else:
            print(f"[!] PowerShell не справился, загрузите Tor Expert Bundle вручную...\n"
                  f"[!] {TOR_URL}")
    except Exception as err:
        print(f"В процессе загрузки Tor возникла ошибка:\n{err}")
        print("Продолжаю настройку, пропуская загрузку Tor...")
        pass

    if archive_path.stat().st_size == 0:
        raise RuntimeError("Скачанный архив пуст.")

    # Распаковка
    print("[*] Распаковка архива...")
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=TOR_DIR)
    except Exception as err:
        raise RuntimeError(f"Ошибка распаковки: {err}")
    finally:
        archive_path.unlink(missing_ok=True)

    print("[+] Tor успешно установлен!")
    time.sleep(1)


def download_with_pwsh(url, dest_path):
    """Загрузка через PowerShell WebClient"""

         # Подготовка папок
    dest_dir = os.path.dirname(dest_path)
    if dest_dir and not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)

    # 1. Уведомление пользователя
    print(f"Файл будет сохранен в: {dest_path}")
    print("Внимание: загрузка может занять несколько минут.")
    print("Ниже появится прогресс-бар, он отображает статус загрузки.")

    # 2. Код, исполняемый в PowerShell (ручной стриминг для прогресса загрузки)
    ps_script = f"""
    $url = "{url}"
    $path = "{dest_path}"

    try {{
        $wc = New-Object System.Net.WebClient
        $stream = $wc.OpenRead($url)
        $totalBytes = [int64]$wc.ResponseHeaders["Content-Length"]
        $fileStream = [System.IO.File]::Create($path)
        $buffer = New-Object byte[] 128KB
        $totalRead = 0

        while (($read = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {{
            $fileStream.Write($buffer, 0, $read)
            $totalRead += $read
            if ($totalBytes -gt 0) {{
                $percent = [Math]::Floor(($totalRead / $totalBytes) * 100)
                [Console]::Write("`rProgress: $percent% ")
            }}
        }}
        $fileStream.Close()
        $stream.Close()
        Write-Host "`n[Download Completed.]"
    }} catch {{
        # Выбрасываем системную ошибку для перехвата в Python
        Write-Error $_.Exception.Message
        exit 1
    }}
    """

    # 3. Запуск процесса
    process = subprocess.Popen(
        ["powershell", "-NoProfile", "-Command", ps_script],
        stdout=None,            # Прогресс идет в консоль напрямую
        stderr=subprocess.PIPE, # Ошибки ловим отдельно
        text=True,
        encoding="utf-8"
    )

    _, stderr = process.communicate()

    # 4. Обработка результата
    if process.returncode != 0:
        print(f"\n\n[ОШИБКА]: Не удалось загрузить файл.")
        print(f"Пожалуйста, попробуйте ещё раз или скачайте его самостоятельно по ссылке:\n {url}")

        if stderr:
            # Сохраняем "битый" вывод в файл для диагностики
            with open("error_log.txt", "wb") as f:
                f.write(stderr)
            print("Технические детали ошибки сохранены в файл 'error_log.txt'.")
        return False
    else:
        return True


def create_torrc() -> None:
    """Генерирует torrc с путями к файлам, портом и настройками для мостов."""
    DATA_DIR.mkdir(exist_ok=True)

    # Редактируем слеши в путях, чтобы убрать предупреждения в логах tor
    data_dir_win = str(DATA_DIR).replace("/", "/")
    tor_dir_win = str(TOR_DIR).replace("/", "/")

    torrc_content = f"""\
SocksPort {SOCKS_PORT}
ClientTransportPlugin obfs4 exec TOR_DIR\\tor\\pluggable_transports\\lyrebird.exe
DataDirectory {data_dir_win}
GeoIPFile {tor_dir_win}\\data\\geoip
GeoIPv6File {tor_dir_win}\\data\\geoip6
Log notice stdout
# ОБЯЗАТЕЛЬНО добавьте Bridge перед каждой строкой с вашим мостом
UseBridges 1
Bridge 107.191.102.246:11111 03F427B05F658D152B2DBB9A6B25FC722C831174
#Bridge [YOUR][BRIDGE]
"""
    TORRC_PATH.write_text(torrc_content, encoding="utf-8")
    print("[+] Файл torrc создан. (ДОБАВЬТЕ МОСТЫ)")


def create_config_json() -> dict:
    """Сохраняет основные настройки в JSON."""
    config = {
        "tor_exe": str(TOR_EXE),
        "torrc_path": str(TORRC_PATH),
        "data_dir": str(DATA_DIR),
        "tor_dir": str(TOR_DIR),
        "socks_port": int (SOCKS_PORT),
        "time_out": int(300)
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print(f"[+] Конфигурация сохранена в {CONFIG_FILE}")
    return config


# def create_launcher() -> None:
#     """Создаёт .bat файл для простого запуска."""
#     bat_path = BASE_DIR / "tor_proxy.bat"
#     main_script = BASE_DIR / "main.py"
#     bat_content = f'@echo off\npython "{main_script.name}"\npause'
#     bat_path.write_text(bat_content, encoding="utf-8")
#     print(f"[+] Лаунчер создан: {bat_path}")


def add_proxy_to_telegram() -> None:
    """Автоматически добавляет прокси в десктоп-приложение telegram (если установлено).\n
    host:port берутся из констант в start.py"""

    print("\n[*]Пытаюсь добавить прокси в Telegram автоматически...")
    print(" (Если не получилось - добавьте вручную позже)")
    time.sleep(5)
    try:
        webbrowser.open(TG_PROXY_LINK)
    except Exception as err:
        print(f"[!] Возникла ошибка при попытке добавить прокси в телеграм автоматически."
              f"\nКод ошибки:\n {err}.")



def main() -> None:
    print("=== Настройка окружения Tor Proxy ===")

    # 1. Работа с виртуальным окружение (создание, проверка наличия, проверка запуска из-под него)
    check_environment()

    # 2. Проверка/установка Tor Expert Bundle
    if not TOR_EXE.exists():
        print("[*] Не вижу Tor в директории скрипта, начинаю загрузку...")
        tor_download_manager()
    else:
        print("[*] Tor уже присутствует, пропускаю загрузку.")

    # 3. Создание torrc (Tor конфиг)
    create_torrc()

    # 4. Сохраняем состояние в config.json (пути до файлов, порт прокси)
    create_config_json()

    # 5. Создаём лаунчер (run.bat)
    # create_launcher()

    # 6. Автоматическое добавление прокси в телеграм (опционально)
    add_proxy_to_telegram()

    # 7. Принты с инструкциями
    print(" === Настройка завершена! ===\n")
    print(f"[!] Чтобы запустить тор-прокси в дальнейшем:\n   1. Дважды кликните start_proxy.bat")
    print(" === НЕ ЗАБУДЬТЕ ДОБАВИТЬ МОСТЫ В КОНФИГ! (torrc) (открыть можно блокнотом) ===")
    print(" === НЕ ЗАБУДЬТЕ ДОБАВИТЬ МОСТЫ В КОНФИГ! (torrc) (открыть можно блокнотом) ===")
    print(" === НЕ ЗАБУДЬТЕ ДОБАВИТЬ МОСТЫ В КОНФИГ! (torrc) (открыть можно блокнотом) ===\n")
    print(" === ВАЖНО - Ваше прокси работает ТОЛЬКО когда тор запущен и ТОЛЬКО когда он ===\n"
          " === установил соединение - Вы должны видеть Bootstrapped 100% в его выводе === .\n "
          "=== Если соединение не доходит до 100% - смените мосты === ")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Прервано пользователем.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] Критическая ошибка: {e}")
        sys.exit(1)
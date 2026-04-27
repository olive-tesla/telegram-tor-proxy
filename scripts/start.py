"""
Скрипт с логикой первого запуска и настройками работы:
- Скачивает (если не нашёл в корне/tor) Tor Expert Bundle с офф. Сайта, используя PowerShell WebClient (на Windows)
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
import socket
import venv  # noqa

from core.utils import check_is_docker
from core.constants import (BASE_DIR, ARCHIVE_NAME, CONFIG_FILE, TORRC_PATH, DATA_DIR, TOR_DIR, TOR_EXE, BRIDGES_FILE)
from core.settings import  (TOR_DOWNLOAD_URL,
                      FINAL_PROXY_HOSTNAME, FINAL_PROXY_PORT, TG_PROXY_LINK, IS_DOCKER)


def tor_download_manager() -> None:
    """Управляет процессом загрузки tor expert bundle,
    метод загрузки выбирается в блоке try:
     Не загружает сам напрямую, за это отвечает другая функция"""
    TOR_EXE.mkdir(exist_ok=True)
    archive_path = BASE_DIR / ARCHIVE_NAME
    manual_download = True

    if sys.platform == "win32":
        try:
            print("\n[*] Пробую скачать через PowerShell...")
            if download_with_pwsh(TOR_DOWNLOAD_URL, archive_path):
                print("\n[!] Загрузка прошла успешно!")
            else:
                print(f"[!] PowerShell не справился, загрузите Tor Expert Bundle вручную...\n"
                      f"[!] {TOR_DOWNLOAD_URL}")
        except Exception as err:
            print(f"В процессе загрузки Tor возникла ошибка:\n{err}")
            print("Продолжаю настройку, пропуская загрузку Tor...")
            pass
        if archive_path.stat().st_size == 0:
            raise RuntimeError("Скачанный архив пуст.")
    else:
        if not IS_DOCKER:
            manual_download = False # заглушка, нужно будет убрать
            pass
        #todo логика unix non-docker (загрузить вручную). apt\git clone\tor expert bundle

        else:
            manual_download = False # заглушка, но вероятно так и оставить
            pass
        # todo unix докер, ставится автоматически в контейнере, возможно стоит добавить проверку, хотя бы which tor

    # Распаковка
    if manual_download:
        print("[*] Распаковка архива...")
        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(path=TOR_DIR)
        except Exception as err:
            raise RuntimeError(f"Ошибка распаковки: {err}")
        finally:
            archive_path.unlink(missing_ok=True)
    print("[+] Загрузчик Tor завершил работу!")


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
            with open("error_log.txt", "wb", encoding="utf-8") as f:
                f.write(stderr)
            print("Технические детали ошибки сохранены в файл 'error_log.txt'.")
        return False
    else:
        return True


def create_torrc(bridges=None) -> None:
    """Генерирует torrc с путями к файлам, портом и настройками для мостов."""
    # DATA_DIR.mkdir(exist_ok=True)

    # Убедиться, что сохраним пути с прямым слешем
    data_dir_win = str(DATA_DIR).replace("\\", "/")
    tor_dir_win = str(TOR_DIR).replace("\\", "/")

    torrc_content = f"""\
SocksPort {FINAL_PROXY_PORT if not IS_DOCKER else f"{FINAL_PROXY_HOSTNAME}:{FINAL_PROXY_PORT}"}
CookieAuthentication 1
DormantCanceledByStartup 1
#ClientTransportPlugin conjure exec {tor_dir_win}/tor/pluggable_transports/lyrebird.exe
ClientTransportPlugin webtunnel exec {tor_dir_win}/tor/pluggable_transports/lyrebird.exe
ClientTransportPlugin obfs4 exec {tor_dir_win}/tor/pluggable_transports/lyrebird.exe
ClientTransportPlugin snowflake exec {tor_dir_win}/tor/pluggable_transports/lyrebird.exe
DataDirectory {data_dir_win}
GeoIPFile {data_dir_win}/geoip
GeoIPv6File {data_dir_win}/geoip6
# stdout - логи в консоль (по умолчанию)
Log notice stdout
# так можно сделать вывод логов в файл, с примером пути для windows
# Log notice file D:/tor/log.txt
{"UseBridges 1\n"}{"\n".join(bridges) if bridges else ""}
"""
    TORRC_PATH.write_text(torrc_content, encoding="utf-8")
    print("[+] Файл torrc создан.")


def create_config_json() -> dict:
    """Сохраняет основные настройки в JSON."""
    config = {
        "tor_exe": str(TOR_EXE),
        "torrc_path": str(TORRC_PATH),
        "data_dir": str(DATA_DIR),
        "tor_dir": str(TOR_DIR),
        "proxy_port": int (FINAL_PROXY_PORT),
        "time_out": int(300),
        "is_docker": bool(check_is_docker())
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print(f"[+] Конфигурация сохранена в {CONFIG_FILE}")
    return config


def add_proxy_to_telegram() -> None:
    """Автоматически добавляет прокси в Telegram Desktop (если установлен).
    """

    print("\n[*]Пытаюсь добавить прокси в Telegram автоматически...")
    print(" (Если не получилось - добавьте вручную позже)")
    time.sleep(3)
    try:
        webbrowser.open(f"{TG_PROXY_LINK}")
    except Exception as err:
        print(f"[!] Возникла ошибка при попытке добавить прокси в телеграм автоматически."
              f"\nКод ошибки:\n {err}.")


def get_bridges_from_file() -> list[str] | Exception:
    """Читаем мосты из BRIDGES.txt."""
    # Проверяем, существует ли файл
    if not BRIDGES_FILE.exists():
        return FileNotFoundError(f"[!]Файл с мостами не найден по адресу: {BRIDGES_FILE}")
        #todo добавить логику работы, если файл с мостами пустой.
        # вариант - попытаться подключиться напрямую без мостов, убирая флаг UseBridges 1 в torrc
        # либо вызвать здесь функцию получения новых мостов (сначала её нужно написать конечно)

    # Работа с файлом BRIDGES.txt
    try:
        with open(BRIDGES_FILE, "r", encoding="utf-8") as f:
            # list comprehension не пустую строку с мостом сохраняем в формате, понятном Tor: "{Bridge} {мост_из_файла}"
            bridges = [f"{"Bridge"} {stripped_line}" for line in f if (stripped_line:= line.strip())]
            #todo - при полной автоматизации - здесь должен быть полноценный "чекер" мостов, по хорошему
            # async\отдельный поток с чекером (сначала нужно автоматизировать получение мостов).
            return bridges

    except Exception as err:
        print("Проблема при чтении мостов! Добавьте их вручную...")
        print(err)
        return [f"#Bridges '.....' "]


def check_is_port_used() -> bool:
    """
    Проверяет занятость порта. Возвращает True если занят
    Если свободен или возникла ошибка False.
    """

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', int(FINAL_PROXY_PORT))) == 0

    except (TypeError, ValueError, socket.error):
        return False


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
import json
import os
import platform
import socket
import subprocess
import sys
import tarfile
import time
import venv  # noqa
import webbrowser
from pathlib import Path
from core.constants import BASE_DIR, DATA_DIR, TOR_DIR, DEFAULT_PORT, TORRC_PATH, TOR_EXE, CONFIG_FILE, BRIDGES_FILE, \
    ARCHIVE_NAME
from core.settings import FINAL_PROXY_PORT, FINAL_PROXY_HOSTNAME, IS_DOCKER, TOR_DOWNLOAD_URL, TG_PROXY_LINK


def get_proxy_hostname() -> str:
    """
    Вызывает check_is_docker(), в зависимости от результата возвращает нужный хост
    :return: host: str ("0.0.0.0" or "127.0.0.1")
    """

    host = "0.0.0.0" if check_is_docker() else "127.0.0.1"
    return host


def get_proxy_port() -> int:
    """
    Определяет порт для записи в config.json.
    :return: port: int
    """

    # Приоритет переменной окружения (для Docker), иначе дефолт 9090
    port = int(os.environ.get("APP_PORT", DEFAULT_PORT))

    if is_port_in_use(port):
        print(f"Предупреждение: Порт {port} занят, но будет использован по умолчанию."
              f"Изменить можно вручную в config.json.")

    return port


def check_is_docker() -> bool:
    """
    проверка в докер-контейнере мы или нет
    :return: bool
    """
    return os.environ.get("RUNNING_IN_DOCKER") == "true"


def is_port_in_use(port: int) -> bool:
    """
    Проверяет, занят ли порт.

    :param port: int
    :return: bool
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', int(port))) == 0

    except Exception as err:
        print(f"Ошибка проверки доступности порта:\n{err}")
        return False # Если ошибка, считаем порт свободным


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
        print("Ошибка при проверке занятости порта!")
        return False


def check_os() ->  str:
    """Возвращает название ОС."""
    print(platform.system().lower())
    return platform.system().lower()


def create_environment():
    print("-- Создание виртуального окружения...")

    try:
        venv.create(".venv", with_pip=True)
        install_dependencies()
    except Exception as err:
        print(f"-- Ошибка при создании .venv: {err}")


def install_dependencies(python_exe=sys.executable):

    print("[*] Установка зависимостей...")

    req_file = Path("requirements.txt")

    try:
        # Ставим всё из requirements.txt либо только colorama
        if req_file.exists:
            subprocess.run([python_exe, "-m", "pip", "install", "-r", str(req_file)], check=True)
        else:
            print("[*] requirements.txt не найден, ставлю только colorama...")
            subprocess.run([python_exe, "-m", "pip", "install", "colorama"], check=True)
    except Exception as err:
        print(f"-- Ошибка при установке зависимостей: {err}")


def check_environment():
    # 1. Проверяем, запущены ли мы из .venv
    is_venv = sys.prefix != sys.base_prefix

    #провалимся внутрь, только если скрипт работает не из-под .venv
    if not is_venv:
        #пробуем найти и перезапуститься из-под него, если его нет - создаём

        # собираем пути (нужны для проверки наличия .venv)
        venv_dir = ".venv"
        venv_path = BASE_DIR / venv_dir
        python_exe = os.path.join(BASE_DIR, '.venv', 'Scripts', 'python.exe')

        # Проверяем, что .venv существует (провалимся внутрь если найден)
        if venv_path.exists() and venv_path.is_dir():
            print("Использую существующее виртуальное окружение (.venv)...")
            sys.exit(subprocess.run([python_exe, sys.argv[0]]).returncode)

        else:
            print(".venv нет, создаю окружение...")
            create_environment()
            print('Виртуальное окружение создано. Продолжу работу из него...')

            # 3. Перезапускаем этот же скрипт, но уже из-под .venv
            sys.exit(subprocess.run([python_exe, sys.argv[0]]).returncode)

    else:
        # print(f"Используемый Python: {sys.executable}")
        print(f"Запущено в окружении: {sys.prefix}")


def create_torrc(bridges=None) -> None:
    """Генерирует torrc с путями к файлам, портом и настройками для мостов."""

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
# вывод "сырых" логов tor в файл (на случай проблем)
Log notice file {BASE_DIR}/tor_logs.txt
{"UseBridges 1" if bridges else ""}
{"\n".join(bridges) if bridges else ""}
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


def get_bridges_from_file() -> list[str] | None | Exception:
    bridges = None
    """Читаем мосты из BRIDGES.txt."""

    # Проверяем, существует ли файл
    if not BRIDGES_FILE.exists():
        return bridges
        #ЗДЕСЬ можно вызвать функцию получения новых мостов (сначала её нужно написать конечно)

    # Работа с файлом BRIDGES.txt, он существует
    try:
        with open(BRIDGES_FILE, "r", encoding="utf-8") as f:
            #list comprehension - не пустую строку с мостом сохраняем в формате, понятном Tor: "{Bridge} {мост_из_файла}"
            bridges = [f"{"Bridge"} {stripped_line}" for line in f if (stripped_line:= line.strip())]

            #todo - для полной автоматизации - здесь должен быть полноценный "чекер" мостов, по хорошему
            # async\отдельный поток с чекером (сначала нужно автоматизировать получение мостов).
            # вероятно это избыточно
            return bridges

    except Exception as err:
        print("Проблема при чтении мостов! Добавьте их вручную...")
        print(err)
        return [f"#Bridges '.....' "]


def tor_download_manager() -> None:
    """Управляет процессом загрузки tor expert bundle,
    метод загрузки выбирается в блоке try:
     Не загружает сам напрямую, за это отвечает другая функция"""
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
        else:
            #удаляем архив, если успешно распаковали
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


def main():
    print('use main.py as entry point')


if __name__ == "__main__":
    main()



import os
import platform
import socket
import subprocess
import sys
import venv  # noqa
from core.constants import DEFAULT_PORT, BASE_DIR


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


def check_os() ->  str:
    """Возвращает название ОС."""
    print(platform.system().lower())
    return platform.system().lower()


def create_environment():
    print("-- Создание виртуального окружения...")

    try:
        venv.create(".venv", with_pip=True)
        install_dependencies(python_exe=os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe"))
    except Exception as err:
        print(f"-- Ошибка при создании .venv: {err}")


def install_dependencies(python_exe: str = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")):
    print("[*] Установка зависимостей...")

    req_file = "requirements.txt"

    try:
        # сначала обновляем pip
        #subprocess.check_call([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"])

        # Ставим всё из requirements.txt либо только colorama
        if os.path.exists(req_file):
            subprocess.check_call([str(python_exe), "-m", "pip", "install", "-r", req_file])
        else:
            print("[*] requirements.txt не найден, ставлю только colorama...")
            subprocess.check_call([str(python_exe), "-m", "pip", "install", "colorama"])
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


def main():
    print('use main.py as entry point')


if __name__ == "__main__":
    main()



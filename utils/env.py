import logging
import subprocess
import sys
from pathlib import Path

from constants import BASE_DIR

logger = logging.getLogger(__name__)


def check_os_name() -> str:
    """Возвращает используемую ОС."""
    return sys.platform  # fallback

def is_running_in_docker() -> bool:
    """
    Возвращает True, если скрипт выполняется внутри Docker-контейнера.
    Проверяется наличие файла /.dockerenv (стандартный маркер Docker).
    """
    return Path("/.dockerenv").is_file()

def is_venv_active() -> bool:
    """True, если текущий процесс уже запущен внутри виртуального окружения."""
    return sys.prefix != sys.base_prefix

def is_venv_exists(venv_dir: Path) -> bool:
    """True, если venv существует (директория)."""
    return venv_dir.is_dir()

def _get_venv_python(venv_dir: Path) -> Path:
    """Возвращает путь к интерпретатору Python внутри venv."""
    if check_os_name() == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"

def create_venv(venv_dir: Path) -> None:
    """Создаёт виртуальное окружение с помощью модуля venv."""

    logger.info("Создаю виртуальное окружение %s...", venv_dir)
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        check=True,
        capture_output=True,
        text=True
    )

def restart_under_venv(venv_dir: Path) -> None:
    """
    Перезапускает текущий скрипт под Python из указанного venv.
    Процесс завершается с кодом возврата дочернего процесса.
    """
    python_exe = _get_venv_python(venv_dir)
    if not python_exe.is_file():
        logger.error("Интерпретатор не найден: %s", python_exe)
        sys.exit(1)

    logger.info("Перезапуск под %s...", python_exe.relative_to(BASE_DIR))
    # sys.argv содержит [скрипт, аргументы...]
    sys.exit(subprocess.run([str(python_exe), *sys.argv]).returncode)

def ensure_venv(venv_dir: Path) -> None:
    """
    Гарантирует, что скрипт выполняется внутри виртуального окружения.
    - Если уже в venv — ничего не делает.
    - Если .venv существует, но мы не внутри — перезапускает.
    - Если .venv не существует — создаёт и перезапускает.
    """
    if is_venv_active():
        logger.info("Работаем внутри виртуального окружения.")
        return

    if not is_venv_exists(venv_dir):
        create_venv(venv_dir)

    restart_under_venv(venv_dir)


def install_dependencies():
    """Устанавливает зависимости из requirements.txt """
    logger.info("Установка зависимостей...")

    req_file = Path("requirements.txt")

    try:
        if req_file.is_file():
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                           check=True,
                           capture_output=True,
                           text=True)
            logger.info("Зависимости успешно установлены.")
    except Exception as err:
        logger.error("Ошибка при установке зависимостей: %s", err)
        return False
    return True
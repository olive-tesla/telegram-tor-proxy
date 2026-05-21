import os
import socket
import time
import webbrowser
import logging

from constants import DEFAULT_PORT
from utils.env import is_running_in_docker

logger = logging.getLogger(__name__)


def get_proxy_hostname() -> str:
    """
    Возвращает актуальный хост в зависимости от окружения
    :return: host: str ("0.0.0.0" or "127.0.0.1")
    """

    host = "0.0.0.0" if is_running_in_docker() else "127.0.0.1"
    return host


def get_proxy_port() -> int:
    """
    Определяет порт для записи в config.json.
    :return: port: int
    """

    # Приоритет переменной окружения (для Docker), иначе дефолт 9090
    port = int(os.environ.get("APP_PORT", DEFAULT_PORT))

    # if not is_port_free(get_proxy_hostname(),port):
    #     logger.error(f"Предупреждение: Кажется, порт {port} занят, но все равно будет использован. "
    #           f"Изменить можно вручную в config.json.")
        #todo доделать is_port_free, перенести эту логику отсюда

    return port


def is_port_free(host: str, port: int) -> bool:
    """
    Проверяет, можно ли занять указанный порт на хосте.
    Возвращает True, если порт свободен, иначе False.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True

    except OSError as err:
        # 10048 (Address already in use) на Windows или 98 (Address in use) на Linux
        if err.errno in (10048, 98, 10013):
            logger.error(f"Порт {host}:{port} уже занят.")
        else:
            logger.error(f"Ошибка проверки порта {host}:{port} — {err}")
        return False
    except Exception as err:
        logger.error(f"Непредвиденная ошибка при проверке порта: {err}")
        return False


def add_proxy_to_telegram() -> None:
    """Автоматически добавляет прокси в Telegram Desktop (если установлен).
    """

    logger.info("Пытаюсь добавить прокси в Telegram автоматически...")
    logger.info(" (Если не получилось - добавьте вручную позже)\n")
    time.sleep(3)
    try:
        webbrowser.open(f"{TG_PROXY_LINK}")
    except Exception as err:
        logger.error(f"Возникла ошибка при попытке добавить прокси в телеграм автоматически."
              f"\nКод ошибки:\n {err}.")


#  --- ДИНАМИЧЕСКИЕ КОНСТАНТЫ ---

# получаем итоговые хост:порт
FINAL_PROXY_PORT = get_proxy_port()
FINAL_PROXY_HOSTNAME = get_proxy_hostname()
#генерируем прокси-ссылку для Telegram Desktop, на основе итоговых хост:порт
TG_PROXY_LINK = f"tg://socks?server={FINAL_PROXY_HOSTNAME}&port={FINAL_PROXY_PORT}"

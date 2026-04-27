#  --- ДИНАМИЧЕСКИЕ КОНСТАНТЫ ---
from core.utils import get_proxy_port, get_proxy_hostname, check_is_docker
# получаем итоговые хост:порт
FINAL_PROXY_PORT = get_proxy_port()
FINAL_PROXY_HOSTNAME = get_proxy_hostname()

# проверяем в докере контейнере мы или нет
IS_DOCKER = check_is_docker()

#генерируем прокси-ссылку для Telegram Desktop, на основе итоговых хост:порт
TG_PROXY_LINK = f"tg://socks?server={FINAL_PROXY_HOSTNAME}&port={FINAL_PROXY_PORT}"

# отсюда скрипт попытается скачать архив tor expert bundle, если не нашёл его в подпапке /tor
TOR_DOWNLOAD_URL = (
"https://archive.torproject.org/tor-package-archive/torbrowser/15.0.9/"
"tor-expert-bundle-windows-x86_64-15.0.9.tar.gz"
)


from sys import platform
from pathlib import Path

#  --- КОНСТАНТЫ ---
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
BRIDGES_FILE = BASE_DIR / "BRIDGES.txt"
TORRC_PATH = BASE_DIR / "torrc"
TOR_DIR = BASE_DIR / "tor"
DATA_DIR = TOR_DIR / "data"

if platform == "win32":
    TOR_EXE = TOR_DIR / "tor" / "tor.exe"
    # отсюда скрипт попытается скачать архив tor expert bundle, если не нашёл его в подпапке /tor
    TOR_DOWNLOAD_URL = (
        "https://archive.torproject.org/tor-package-archive/torbrowser/15.0.9/"
        "tor-expert-bundle-windows-x86_64-15.0.9.tar.gz"
    )
    #TOR_DOWNLOAD_URL = "https://archive.torproject.org/tor-package-archive/torbrowser/15.0.14/tor-expert-bundle-windows-x86_64-15.0.14.tar.gz"

else:
    TOR_EXE = TOR_DIR / "tor" / "tor"
    TOR_DOWNLOAD_URL = "https://archive.torproject.org/tor-package-archive/torbrowser/15.0.14/tor-expert-bundle-linux-x86_64-15.0.14.tar.gz"

EXTENSION_PATTERN = "*.tar.gz"
ARCHIVE_NAME = "tor_expert_bundle*.tar.gz"
ARCHIVE_PATH = BASE_DIR / ARCHIVE_NAME
DEFAULT_PORT = 9090
DEFAULT_TIMEOUT = 600
# порт по умолчанию (используется введённый от юзера | этот)
# для справки: (по умолчанию, тор (если не переназначено в конфиге) попытается слушать порт 9050)
from sys import platform
from pathlib import Path

#  --- КОНСТАНТЫ ---
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.json"
BRIDGES_FILE = BASE_DIR / "BRIDGES.txt"
TORRC_PATH = BASE_DIR / "torrc"
TOR_DIR = BASE_DIR / "tor"
DATA_DIR = TOR_DIR / "data"
if platform == "win32":
    TOR_EXE = TOR_DIR / "tor" / "tor.exe"
else:
    TOR_EXE = TOR_DIR / "tor" / "tor"

ARCHIVE_NAME = "tor_expert_bundle.tar.gz"
DEFAULT_PORT = 9090
# порт по умолчанию (используется введённый от юзера | этот)
# для справки: (по умолчанию, тор (если не переназначено в конфиге) попытается слушать порт 9050)
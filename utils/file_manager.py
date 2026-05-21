import json
import tarfile
import logging
from pathlib import Path

from constants import ARCHIVE_PATH, TOR_DIR, DATA_DIR, TORRC_PATH, TOR_EXE, CONFIG_FILE, BRIDGES_FILE, BASE_DIR, \
    DEFAULT_TIMEOUT
from utils.env import is_running_in_docker
from utils.proxy import FINAL_PROXY_PORT, FINAL_PROXY_HOSTNAME

logger = logging.getLogger(__name__)


def find_file(root_dir: Path, file_pattern: str|None = None, extension_pattern: str|None = None) -> Path|None:
    """
    Ищет файл в папке по шаблону имени и/или расширению.
    Возвращает объект Path(путь до) первого найденного файла или None.
    """
    # 1. Сначала ищем по шаблону имени, если передан
    if file_pattern:
        file = next(root_dir.glob(file_pattern), None)
        if file:
            return file

    # 2. Если по шаблону не нашли (или он не задан), пробуем найти по расширению
    if extension_pattern:
        # Форматируем, на случай если получим, например 'tar.gz' вместо '*.tar.gz'
        search_ext = extension_pattern if extension_pattern.startswith("*") else f"*.{extension_pattern.lstrip('.')}"

        file = next(root_dir.glob(search_ext), None)
        if file:
            return file

    # 3. Если ничего не нашли или аргументы не были переданы
    return None


def archive_extract(file_path: Path|None, extract_to: Path) -> None:
    """Распаковывает архив tar.gz и удаляет после распаковки, если успешно. - """
    logger.info("Распаковка архива...")
    try:
        with tarfile.open(file_path, "r:gz") as tar:
            tar.extractall(path=extract_to)
    except Exception as err:
        raise RuntimeError(f"Ошибка распаковки: {err}")
    else:
        #удаляем архив, если успешно распаковали
        logger.info("Распаковка прошла успешно, архив больше не нужен, удаляю его...")
        file_path.unlink(missing_ok=True)


def create_torrc(bridges=None) -> None:
    """Генерирует torrc с путями к файлам, портом и настройками для мостов."""

    # Убедиться, что сохраним пути с прямым слешем
    data_dir_win = str(DATA_DIR).replace("\\", "/")
    tor_dir_win = str(TOR_DIR).replace("\\", "/")

    torrc_content = f"""\
SocksPort {FINAL_PROXY_PORT if not is_running_in_docker() else f"{FINAL_PROXY_HOSTNAME}:{FINAL_PROXY_PORT}"}
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
    logger.info("Файл torrc обновлён.")


def create_config_json() -> dict:
    """Сохраняет основные настройки в JSON."""
    config = {
        "tor_exe": str(TOR_EXE),
        "torrc_path": str(TORRC_PATH),
        "data_dir": str(DATA_DIR),
        "tor_dir": str(TOR_DIR),
        "proxy_port": int (FINAL_PROXY_PORT),
        "time_out": int(DEFAULT_TIMEOUT),
        "is_docker": bool(is_running_in_docker())
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    logger.info("Конфигурация сохранена в %s",CONFIG_FILE)
    return config


def get_bridges_from_file() -> list[str] | None | Exception:
    bridges = None #todo typo
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
        logger.error("Проблема при чтении мостов! Добавьте их вручную...")
        logger.error(err)
        return [f"#Bridges '.....' "]
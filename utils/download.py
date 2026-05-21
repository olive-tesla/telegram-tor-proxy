import os
import pathlib
import subprocess
import sys
from pathlib import Path
from shutil import which
import logging

from constants import TOR_DOWNLOAD_URL, ARCHIVE_PATH, EXTENSION_PATTERN, BASE_DIR, ARCHIVE_NAME
from utils.env import is_running_in_docker
from utils.file_manager import find_file

logger = logging.getLogger(__name__)


def find_powershell():
    """Возвращает имя исполняемого файла PowerShell (предпочитает pwsh)."""
    if which("pwsh"):
        return "pwsh"
    if sys.platform == "win32" and which("powershell"):
        return "powershell"
    return None


def tor_download_manager() -> Path|bool|None:
    """
    Управляет процессом установки tor expert bundle,
    сначала проверяет, есть ли уже архив в корне проекта
    (если пользователь загрузил вручную), если нет -
    пытается скачать. Приоритет - PowerShell > wget

    Возвращает True, если архив найден\загружен
    """

    # Сначала пробуем найти архив в корне проекта (на случай, если пользователь уже загрузил вручную)
    logger.debug("Пробую найти архив в корне проекта")
    archive_exists = find_file(BASE_DIR,ARCHIVE_NAME,EXTENSION_PATTERN)

    if archive_exists:
        logger.debug("tor_download_manager() возвращает путь к существующему архиву, без загрузки."
                     "Путь к архиву:\n --- %s",archive_exists)
        return archive_exists

    logger.info("Tor не установлен и архив не найден, начинаю загрузку...")
    download_success: bool = False
    powershell_exists: str | None = find_powershell()

    # используем PowerShell в приоритете для загрузки
    if powershell_exists is not None:
        try:
            logger.info("Пробую скачать через PowerShell...")
            if download_with_pwsh(url=TOR_DOWNLOAD_URL,dest_path=ARCHIVE_PATH, powershell_exe=powershell_exists):
                logger.info("Загрузка прошла успешно!")
                download_success = True

            else:
                logger.error("[!] PowerShell не справился, загрузите Tor Expert Bundle вручную...\n"
                             "[!] %s",TOR_DOWNLOAD_URL)
                download_success = False

        except Exception as err:
            logger.error("В процессе загрузки Tor возникла ошибка:\n%s",err)
            logger.error("[!] Загрузите Tor Expert Bundle вручную, положите архив в корень проекта...\n"
                  "[!] %s",TOR_DOWNLOAD_URL)
            download_success = False

    # если pwsh нет, пробуем через wget
    else:
        is_docker = is_running_in_docker()
        if not is_docker:
            # логика загрузки на linux macos non-docker
            if _download_with_wget(url=TOR_DOWNLOAD_URL,dest_path=ARCHIVE_PATH):
                download_success = True
            else:
                download_success = False


        else:
            # unix docker, пока просто дублировал логику
            if _download_with_wget(url=TOR_DOWNLOAD_URL,dest_path=ARCHIVE_PATH):
                download_success = True
            else:
                download_success = False
            pass
    # todo можно добавить попытку загрузки через зеркало

    logger.info("Установщик Tor завершил работу!")
    return download_success


def _download_with_wget(url: str, dest_path: str) -> bool:
    """Резервная загрузка через wget с прогресс-баром."""
    try:
        process = subprocess.Popen(
            ["wget", "-O", dest_path, url],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # wget пишет прогресс в stderr
            text=True,
            encoding="utf-8"
        )
        for line in process.stdout:
            print(line, end="", flush=True)

        process.wait()
        return process.returncode == 0
    except Exception as e:
        logger.error(f"\n[ОШИБКА] Не удалось загрузить файл через wget: {e}")
        return False


def download_with_pwsh(url: str, dest_path: Path, powershell_exe:str) -> bool:
    """Загрузка архива через PowerShell WebClient с прогресс-баром."""

    # PowerShell-скрипт
    ps_script = r'''
    $Url = $env:PWSH_DOWNLOAD_URL
    $Path = $env:PWSH_DOWNLOAD_PATH

    $wc = $null
    $stream = $null
    $fileStream = $null

    try {
        $wc = New-Object System.Net.WebClient
        $stream = $wc.OpenRead($Url)
        $totalBytes = [int64]$wc.ResponseHeaders["Content-Length"]
        $fileStream = [System.IO.File]::Create($Path)
        $buffer = New-Object byte[] 128KB
        $totalRead = 0

        while (($read = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
            $fileStream.Write($buffer, 0, $read)
            $totalRead += $read
            if ($totalBytes -gt 0) {
                $percent = [Math]::Floor(($totalRead / $totalBytes) * 100)
                $downloadedMB = [Math]::Round($totalRead/1MB, 1)
                $totalMB = [Math]::Round($totalBytes/1MB, 1)
                [Console]::Write("`rDownloaded $downloadedMB MB of $totalMB MB ($percent%) ")
            }
        }
        Write-Host "`n[Download Completed.]"
    }
    catch {
        Write-Error $_.Exception.Message
        exit 1
    }
    finally {
        if ($fileStream) { $fileStream.Dispose() }
        if ($stream) { $stream.Dispose() }
        if ($wc) { $wc.Dispose() }
    }
    '''

    env = os.environ.copy()
    env["PWSH_DOWNLOAD_URL"] = url
    env["PWSH_DOWNLOAD_PATH"] = str(dest_path.as_posix()).replace("*", "")

    # 1. Уведомление пользователя
    logger.info("Файл будет сохранен по пути: %s", env["PWSH_DOWNLOAD_PATH"])
    logger.info("Ниже появится прогресс-бар загрузки.")

    try:
        process = subprocess.Popen(
            [powershell_exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script], env=env)

        process.communicate()
        # todo обработку ошибок если падает здесь (принудительно попробовать другой метод загрузки\загрузить вручную)

        if process.returncode != 0:
            logger.error("[ОШИБКА] Не удалось загрузить файл через Powershell")
            logger.error("Пожалуйста, попробуйте ещё раз или скачайте файл вручную:\n%s", url)
            return False

    except Exception as e:
        logger.error("[ОШИБКА] Не удалось загрузить файл через Powershell: %s", e)
        logger.error("Пожалуйста, попробуйте ещё раз или скачайте файл вручную:\n%s", url)
        return False

    return True
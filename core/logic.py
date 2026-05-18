"""
Основной скрипт для запуска Tor SOCKS5 прокси.
Для запуска использует конфигурацию из config.json, созданную start.py раннее
Допустимо редактировать config.json, например для изменения порта или тайм-аута для watchdog.

Мониторит состояние процесса tor.exe
Пытается перезапустить процесс в случае падения -
Убивает процесс, если соединение не установлено за указанное в watchdog время
По умолчанию - 2 перезапуска, тайм-аут - 300с. порт - 9090
"""

import json
import subprocess
import sys
import time
from subprocess import Popen
from typing import Dict
from colorama import Fore, Style, init as colorama_init
from threading import Timer
from core.constants import CONFIG_FILE
from core.settings import TG_PROXY_LINK

colorama_init(autoreset=True)


def load_config() -> Dict|Exception:
    """Проверяет наличие config.json и загружает настройки из него."""
    # Проверяем, существует ли уже конфиг файл
    if not CONFIG_FILE.exists():
        return FileNotFoundError(f"[!]Файл конфигурации не найден по адресу: {CONFIG_FILE}")

    # Работа с файлом
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as err:
        print(f"[!] Ошибка при чтении config.json \n {err}")
        return err

    # Проверяем обязательные ключи
    required = ["tor_exe", "torrc_path", "proxy_port", "is_docker"]
    for key in required:
        if key not in config:
            return KeyError(f"{Fore.RED}[!]В конфигурации отсутствует ключ '{key}'")
    return config


def run_tor_proxy(tor_exe: str, torrc_path: str, socks_port: int, time_out: int) -> tuple[bool, Popen[str]]:
    """Запускает процесс Tor и выводит статус в реальном времени.
    Запускает watchdog на 300с - если Tor не установит соединение за
    это время - убивает процесс (с попытками перезапуска)"""


    tor_is_ready: bool = False
    watchdog = None
    process = None

    # Принты при начале работы с Tor
    print(f"\n{Fore.MAGENTA}{'=' * 60}")
    print(f"{Fore.CYAN}[*] ЗАПУСК TOR ПРОКСИ")
    print(f"{Fore.WHITE}[*] Адрес: 127.0.0.1  |  Порт: {socks_port}")
    print(f"{Fore.MAGENTA}{'=' * 60}\n")

    # Логика работы с Tor
    try:
        process = subprocess.Popen([tor_exe, "-f", torrc_path],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   text=True,
                                   bufsize=1)

        # Запускаем таймер на 300с (5мин) - Если Tor не установит соединение - убиваем процесс и пробуем ещё раз.
        # Редко - соединение может занимать более 5мин. - тогда, отредактируйте таймер. Но чаще это проблема с мостами.
        watchdog = Timer(time_out, kill_process, args=[process])
        watchdog.start()
        print(f"{Fore.CYAN}[*] === watchdog запущен c тайм-аутом: {time_out} === ")


        #сборщик мусора, перестаёт выводить некоторые логи, по достижению лимита, если тор начинает ими спамить
        collector:int = 0

        for line in process.stdout:
            line = line.strip()
            # Когда цепочка построена на 100%
            if "Bootstrapped 100%" in line and not tor_is_ready:
                tor_is_ready = True
                watchdog.cancel()

                print(f"{Fore.WHITE}{line}")

                #инструкции
                print(f"\n{Fore.GREEN}{Style.BRIGHT}[!!!] СЕТЬ TOR ГОТОВА! [!!!]\n"
                      f"{Fore.CYAN}Ваш прокси теперь работает. \n"
                      f"\n{Fore.WHITE}В формате ссылки для добавления в Telegram:\n"
                      f"{Fore.YELLOW}{TG_PROXY_LINK}")

                # инструкции
                print(f"\n{Fore.WHITE}Скопируйте её в Telegram или откройте в браузере.\n"
                      f"{Fore.WHITE}Либо добавьте прокси вручную: (для десктоп приложения) \n"
                      f"{Fore.MAGENTA}'Settings'-'Advanced'-'Connection Type'-'Add Proxy' \n"
                      f" SOCKS5, Hostname:port- {Fore.MAGENTA}127.0.0.1:{socks_port}")


            # логика обработки логов тора (на случай ошибок)
                #проблема с мостами
            elif "you must specify at least one bridge" in line and not tor_is_ready:
                print(f"\n{Fore.RED}[!] Ошибка в работе Tor! Проблема с конфигом torrc!\n"
                          f"Видимо, указан флаг UseBridges 1 - Тор пытается использовать мост,\n"
                          f"Но не может его найти - Либо вы не добавили его, или добавили не верно.\n"
                          f"ЛИБО закомментируйте UseBridges 1 (если не хотите использовать мосты)\n"
                          f"ЛИБО добавьте корректно мосты! (РЕКОМЕНДУЕТСЯ), ниже пример как должно быть\n"
                          f"UseBridges 1\n"
                          f"Bridge 107.191.102.246:11111 03F427B05F658D152B2DBB9A6B25FC722C831174\n"
                          f"Bridge [ЗДЕСЬ ЕЩЁ ОДИН ВАШ МОСТ, ВЫШЕ ПРИМЕР, ОН НЕ РАБОТАЕТ]\n"
                          f"Изначальный вид ошибки от Tor - {line}")

                # перестаёт выводить эту строку в консоль, если тор начал ей спамить
            elif "Application request when we haven't used client functionality lately" in line:
                collector += 1
                if collector >= 2:
                    continue
                elif collector == 1:
                    print(f"{Style.DIM}{line}")

                    # проверяем застрял ли tor на этапе построения соединения
            elif "Stuck at" in line:
                collector += 1
                if collector >= 2:
                    print(f"{Style.DIM}{line}")
                    print(f"\n{Fore.YELLOW}[*]Кажется, Tor застрял на этапе построения соединения... Но надежда ещё есть.")
                    print(f"{Fore.YELLOW}[*]Попробуйте подождать 3+мин, если не подключится - используйте мосты.")
                    #is_tor_stuck = True

                    # ВАЖНО! - у меня иногда тор подключался напрямую, спустя 60+ connections have failed (3+ минуты)
                    # возможно имеет смысл оставить подключение напрямую или переход на него, если мосты не работают
                    #т.к есть шанс, что даже при блокировке tor, он сможет подключиться напрямую, спустя много попыток
                    # пример ниже

                    # 19:01:45.000 [warn] 11 connections have failed:
                    #19:04:03.000 [warn] 67 connections have failed:
                    #19:04:04.000 [notice] Bootstrapped 14% (handshake): Handshaking with a relay
                    #19:04:04.000 [notice] Bootstrapped 15% (handshake_done): Handshake with a relay done
                    #19:04:04.000 [notice] Bootstrapped 75% (enough_dirinfo): Loaded enough directory info to build circuits
                    #19:04:04.000 [notice] Bootstrapped 90% (ap_handshake_done): Handshake finished with a relay to build circuits
                    #19:04:04.000 [notice] Bootstrapped 95% (circuit_create): Establishing a Tor circuit
                    #19:04:05.000 [notice] Bootstrapped 100% (done): Done

                    #todo 3/3 добавить логику перезапуска Tor\ротацию мостов здесь (перезапуск будет по отработке watchdog)
                    # либо оставить просто watchdog, и передавать в него флаг is_tor_stuck (выше закомментирован)
                    # если True, вместо попытки перезапуска Tor, запросить новые мосты (нужна логика их получения (1,2todo)

            else:
                # Штатный вывод логов Tor (Приглушённый)
                print(f"{Style.DIM}{line}")

    except FileNotFoundError:
        print(f"{Fore.RED}[!] Не найден tor.exe: {tor_exe}")
        print(f"{Fore.RED}[!] Ожидаемый путь: `папка_проекта`/tor/tor/tor.exe")

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[*] Завершение работы...\n"
              f"{Fore.YELLOW}[*] Прервано пользователем")
        try:
            process.kill()
            print(f"{Fore.GREEN}[+] Прокси остановлен.")
        finally:
            sys.exit(1)

    except Exception as err:
        print(f"{err}")

    finally:
        watchdog.cancel()

    return tor_is_ready, process


def kill_process(proc):
    """Функция-страховка: сработает только если время выйдет"""
    if proc.poll() is None:
        print(f"\n{Fore.CYAN}[!] Превышено время ожидания построения цепочки Tor (5 мин). Рестарт...")
        proc.kill()


def start_and_monitor_tor(config):
    """Запускает и перезапускает (в том числе принудительно) tor.exe
    Мониторит состояние Tor соединения - установлено или нет:

    Когда цепочка соединения установлена - Tor выдаёт в лог строку "Bootstrapped 100%"
    это состояние (был такой вывод или нет) хранится в переменной "success".

    Время ожидания до перезапуска (по умолчанию) - 300с. (5 мин.)
    Попыток перезапуска (по умолчанию) - 2. за перезапуск отвечает watchdog
    """
    attempts = 0
    max_attempts = 2
    process = None

    try:
        while attempts < max_attempts:
            success, process = run_tor_proxy(
            tor_exe=config["tor_exe"],
            torrc_path=config["torrc_path"],
            socks_port=config["proxy_port"],
            time_out=config["time_out"]
            )
            if success:
                # Сбрасываем попытки, если успешно запустились
                attempts = 0
                # Ждем смерти процесса (если упадет позже)
                process.wait()
                print("[!] Программа неожиданно закрылась. Попытка перезапуска...")
                continue

            # Сюда попадем, если success == False (таймер убил процесс или он сам упал)
            attempts += 1
            print(f"[-] Tor не смог выстроить соединение, либо возникла иная timeout ошибка \n"
                  f"  (попытка {attempts}/{max_attempts})")

        if attempts < max_attempts:
            time.sleep(2)  # Пауза перед вторым шансом

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[*] Завершение работы...\n"
              f"{Fore.YELLOW}[*] Прервано пользователем")
        process.kill()
        sys.exit(1)





    # Если вышли из цикла, значит попытки исчерпаны
    return RuntimeError("[!] Критическая ошибка: 'Bootstrapped 100%' не получен после всех попыток. Проверьте мосты.")


def main() -> None:
    config = load_config()
    start_and_monitor_tor(config)


if __name__ == "__main__":
    main()
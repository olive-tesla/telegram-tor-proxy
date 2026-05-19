"""
Входная точка скрипта. Определяет дальнейший сценарий исполнения.
Занимается лишь проверкой конфигурации - ОС, Docker, и прочее. (для выбора сценария работы)
Если всё в порядке - вызывает logic.main(), который отвечает за дальнейшую работу тор-прокси

--- Вся проверка состояния в скрипте завязана на config.json: скрипт НЕ УВИДИТ, если проблемы, с другими файлами.---

Сейчас используются фиксировано те мосты, которые указаны в файле BRIDGES.txt на момент запуска скрипта
В НЕГО НУЖНО ДОБАВИТЬ МОСТЫ ВРУЧНУЮ !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

Читайте README.md - там инструкция, где брать мосты и как их добавить.
"""
from core import logic
from core.utils import check_environment, install_dependencies, get_bridges_from_file, create_torrc, IS_DOCKER
from scripts import start
from importlib.util import find_spec


def main():
    ready = False

    # 1. Проверяем из-под какой ОС работаем (на будущее для кросс-платформенности) (отдельная логика под разные ОС)

    #current_os = check_os()
    # print(f"--- (ОС: {check_os()}) ---")

    # 2. если мы не в контейнере - используем .venv
    if not IS_DOCKER:
        check_environment()

    # 3. устанавливаем зависимости (пропускаем, если установлено)
    if find_spec("colorama") is None:
        install_dependencies()

    # 4. Выбор сценария запуска (штатный - в else блоке).
    if isinstance(status := logic.load_config(), Exception):
        # Проваливаемся внутрь только при ошибке с config.json (нормально при первом запуске, т.к конфиг ещё не создан)

        if isinstance(status, FileNotFoundError):  # Сценарий первого запуска (config.json не найден)
            if start.setup():
                ready = True

        elif isinstance(status, KeyError):  # Проблема с ключами в конфиге (крайний случай, нужно разбираться вручную)
            print(f"В конфиге нет нужного ключа\n {status}\n"
                  f"Попробуйте отредактировать вручную или удалить конфиг (удаление заставит скрипт произвести"
                  f"'чистую' установку. Также проверьте torrc конфиг и файлы tor")
            start.create_config_json()

    # 4.1 До-проверка docker статуса (скип если штатный запуск)
    elif IS_DOCKER != status["is_docker"]:
        print(f"Способ запуска изменился: is_docker{IS_DOCKER}, прошлый запуск: is_docker{status['is_docker']}")
        if start.setup():
            ready = True

    else:  # запуск Tor
        ready = True

    # 5. Если всё готово - берём свежие мосты и вызываем логику работы с тор-прокси
    if ready:
        bridges = get_bridges_from_file()
        create_torrc(bridges)
        logic.main()


if __name__ == "__main__":
    main()
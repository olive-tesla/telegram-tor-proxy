"""
Входная точка скрипта. Определяет дальнейший сценарий исполнения.
Занимается лишь проверкой конфигурации - ОС, Docker, и прочее. (для выбора сценария работы)

--- Вся проверка состояния в скрипте завязана на config.json: скрипт НЕ УВИДИТ, если проблемы, с другими файлами.---

Сейчас используются фиксировано те мосты, которые указаны в файле BRIDGES.txt на момент запуска скрипта
В НЕГО НУЖНО ДОБАВИТЬ МОСТЫ ВРУЧНУЮ !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

Читайте README.md - там инструкция, где брать мосты и как их добавить.
"""
from core import logic
from core.utils import check_environment
from core.settings import IS_DOCKER
from scripts import start


def main():
    ready = False
    # 1. Проверяем из-под какой ОС работаем (на будущее для кросс-платформенности) (отдельная логика под разные ОС)
    #current_os = check_os()
    # print(f"--- (ОС: {check_os()}) ---")

    # 2. проверяем в докер-контейнере мы или нет
    #is_docker = check_is_docker()

    # 3. если мы не в контейнере - используем .venv
    if not IS_DOCKER:
        check_environment()

    # Сценарии запуска (штатный - в else блоке).
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


    # Проверка текущего docker статуса и прошлого из конфига (если отличается - пересоздаём конфиг)
    elif IS_DOCKER != status["is_docker"]:
        print(f"Способ запуска изменился: is_docker{IS_DOCKER}, прошлый запуск: is_docker{status['is_docker']}")
        if start.setup():
            ready = True

    else:  # запуск Tor
        ready = True

    if ready:
        bridges = start.get_bridges_from_file()
        start.create_torrc(bridges)
        logic.main()


if __name__ == "__main__":
    main()
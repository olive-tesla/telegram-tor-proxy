@echo off
REM Устанавливаем кодировку UTF-8(для корректного вывода), переходим в директорию проекта
chcp 65001 > nul
cd /d "%~dp0"

REM 1. Проверка наличия Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python не найден. Пожалуйста, установите его с python.org
    echo При установке поставьте галочку "Add Python to PATH".
    pause
    exit /b
)

REM 2. Просто запускаем main.py, далее он сам разберётся, что делать
python main.py

pause




@echo off

REM 1. Проверка наличия Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python was not found. Please, download it from: python.org
    echo Check "Add Python to PATH" during setup.
    pause
    exit /b
)

REM 2. Просто запускаем main.py, далее он сам разберётся, что делать
python main.py

pause




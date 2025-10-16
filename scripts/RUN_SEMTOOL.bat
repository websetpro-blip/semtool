@echo off
echo ========================================
echo   KeySet - Wordstat Parser
echo ========================================
echo.
echo Запуск из: C:\AI\yandex
echo Python: C:\AI\.venv\Scripts\python.exe
echo.

cd /d C:\AI\yandex

echo Проверка виртуального окружения...
if not exist "C:\AI\.venv\Scripts\python.exe" (
    echo ОШИБКА: Виртуальное окружение не найдено!
    pause
    exit /b 1
)

echo Запуск KeySet...
echo.
"C:\AI\.venv\Scripts\python.exe" -m keyset.app.main

if errorlevel 1 (
    echo.
    echo ОШИБКА при запуске KeySet!
    echo Код ошибки: %errorlevel%
    pause
    exit /b %errorlevel%
)

pause

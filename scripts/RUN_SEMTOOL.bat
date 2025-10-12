@echo off
echo ========================================
echo   SemTool - Wordstat Parser
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

echo Запуск SemTool...
echo.
"C:\AI\.venv\Scripts\python.exe" -m semtool.app.main

if errorlevel 1 (
    echo.
    echo ОШИБКА при запуске SemTool!
    echo Код ошибки: %errorlevel%
    pause
    exit /b %errorlevel%
)

pause

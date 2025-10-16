@echo off
echo ========================================
echo   KeySet - DEBUG MODE
echo ========================================
echo.

cd /d C:\AI\yandex

echo Запуск KeySet с отладкой...
echo.

set PYTHONUNBUFFERED=1
"C:\AI\.venv\Scripts\python.exe" -u -c "import sys; sys.stdout.reconfigure(encoding='utf-8'); print('Stage 1: Imports...'); from PySide6.QtWidgets import QApplication; print('Stage 2: QApplication...'); from keyset.app.main import MainWindow; print('Stage 3: Creating app...'); app = QApplication(sys.argv); print('Stage 4: Creating window...'); window = MainWindow(); print('Stage 5: Showing window...'); window.show(); print('Stage 6: Starting event loop...'); sys.exit(app.exec())"

echo.
echo Программа завершена
pause

"""
SemTool - запуск без окна терминала
Использует pythonw.exe для GUI без консоли
"""
import sys
import os

# Добавляем родительскую папку в путь
parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, os.path.dirname(parent_dir))

# Запускаем главное окно
from semtool.app.main import main

if __name__ == "__main__":
    main()

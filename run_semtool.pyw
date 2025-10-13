"""
SemTool - запуск без окна терминала
Использует pythonw.exe для GUI без консоли
"""
import sys
import os

# Получаем путь к директории со скриптом
script_dir = os.path.dirname(os.path.abspath(__file__))

# Добавляем C:\AI\yandex в путь (родительская папка semtool)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Устанавливаем рабочую директорию
os.chdir(parent_dir)

# Запускаем главное окно
from semtool.app.main import main

if __name__ == "__main__":
    main()

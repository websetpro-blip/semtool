# Скрипты запуска SemTool

Эта папка содержит вспомогательные скрипты для запуска и отладки SemTool.

## Файлы

### RUN_SEMTOOL.bat
**Основной скрипт запуска SemTool**

Использует Python из виртуального окружения `C:\AI\.venv\Scripts\python.exe`

Запускает SemTool из правильной директории для корректной работы импортов.

**Запуск:**
```cmd
scripts\RUN_SEMTOOL.bat
```

### RUN_SEMTOOL_DEBUG.bat
**Отладочный скрипт с подробными логами**

Показывает каждый этап запуска:
- Stage 1: Imports
- Stage 2: QApplication
- Stage 3: Creating app
- Stage 4: Creating window
- Stage 5: Showing window
- Stage 6: Starting event loop

Полезен для диагностики проблем запуска.

**Запуск:**
```cmd
scripts\RUN_SEMTOOL_DEBUG.bat
```

### create_shortcut.vbs
**VBS скрипт для создания ярлыка на рабочем столе**

Создает ярлык `SemTool.lnk` на рабочем столе, который запускает `RUN_SEMTOOL.bat`

**Запуск:**
```cmd
cscript scripts\create_shortcut.vbs
```

### test_semtool_startup.py
**Тестовый скрипт для проверки запуска**

Проверяет каждый этап инициализации:
1. Импорты PySide6
2. Импорты semtool.core.db
3. Инициализация схемы БД
4. Создание DB сессии
5. Импорт MainWindow
6. Создание QApplication
7. Создание MainWindow
8. Показ окна

**Запуск:**
```cmd
python scripts\test_semtool_startup.py
```

## Использование

### Быстрый запуск
Для обычного использования:
1. Запустить `RUN_SEMTOOL.bat` напрямую
2. Или использовать ярлык на рабочем столе (создается через `create_shortcut.vbs`)

### Отладка проблем
Если SemTool не запускается или зависает:
1. Запустить `RUN_SEMTOOL_DEBUG.bat`
2. Посмотреть на какой стадии произошла ошибка
3. Или запустить `test_semtool_startup.py` для детальной диагностики

## Требования

- Python 3.13+ в `C:\AI\.venv\`
- Установленные зависимости: `pip install -r requirements.txt`
- Рабочая директория: `C:\AI\yandex\`

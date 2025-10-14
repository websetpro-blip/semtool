# SemTool - Парсер Яндекс.Wordstat

## 🚀 Быстрый старт

### Требования
- Python 3.11+
- Windows 10/11
- 4GB RAM

### Установка

1. Клонировать репозиторий:
```bash
git clone https://github.com/websetpro-blip/semtool.git
cd semtool
```

2. Установить зависимости:
```bash
pip install -r requirements.txt
```

3. Запустить приложение:
```bash
python run_semtool.pyw
```

## 📁 Структура проекта

```
semtool/
├── app/           # GUI интерфейс
├── services/      # Бизнес-логика
├── workers/       # Парсеры и воркеры
├── core/          # База данных и модели
├── styles/        # Темы интерфейса
└── data/          # База данных SQLite
```

## ✨ Основные возможности

- ✅ Парсинг частотности Яндекс.Wordstat
- ✅ Управление аккаунтами Яндекс
- ✅ Групповая обработка ключевых слов
- ✅ Экспорт в CSV
- ✅ Темная/светлая тема

## 🔧 Конфигурация

Аккаунты хранятся в `data/semtool.db` (SQLite).

## 📝 Лицензия

MIT

## 👥 Авторы

- websetpro-blip
- AI Assistant (Factory Droid)

# 🚀 KeySet - Full Pipeline Edition

**Массовый парсинг Wordstat + Direct + Кластеризация**

Версия: 2.0 | Дата: 13.01.2025

---

## 🎯 Что это?

**KeySet Full Pipeline** - это полный цикл анализа семантики:

```
Маски → Wordstat → Direct → Clustering → CSV
```

**Как KeyCollector, но:**
- ✅ Бесплатно
- ✅ Open Source
- ✅ Автоматическая авторизация
- ✅ Современный Qt интерфейс

---

## ⚡ Быстрый старт

```powershell
# 1. Клонируй или обнови
git clone https://github.com/websetpro-blip/keyset.git
cd keyset

# 2. Установи зависимости
pip install -r requirements.txt
python -c "import nltk; nltk.download('stopwords')"

# 3. Запусти
python -m keyset.app.main

# 4. Открой вкладку "🚀 Full Pipeline"
```

**Подробнее:** [QUICK_START.md](QUICK_START.md)

---

## 📊 Возможности

### Full Pipeline:
- **📊 Wordstat** - частотность (60-80 фраз/мин)
- **💰 Direct** - прогноз бюджета и CPC (100 фраз/мин)
- **🔗 Clustering** - группировка по стеммам (NLTK)
- **💾 Export** - CSV с расширенными данными

### Дополнительно:
- ⚡ Турбо-парсер (до 195 фраз/мин)
- 👤 Управление аккаунтами (5 аккаунтов)
- 🔐 Автологин с iframe handling
- 📈 Real-time статистика

---

## 🏗️ Архитектура

```
services/
├── frequency.py    # Wordstat API/scraping
└── direct.py       # Direct forecast

workers/
└── full_pipeline_worker.py  # Async pipeline

app/
├── full_pipeline_tab.py     # Qt GUI
└── main.py                  # Main window

core/
└── db.py          # SQLite WAL + tables
```

---

## 📁 Структура данных

### База данных (WAL режим):
```sql
frequencies (phrase, freq, region, processed)
forecasts (phrase, cpc, impressions, budget)
clusters (stem, phrases, avg_freq, total_budget)
```

### CSV экспорт:
```
Фраза; Частотность; CPC; Показы; Бюджет; Группа; Размер группы; Средняя частота группы
```

---

## 🎓 Примеры использования

### 1. Анализ конкурентов
```
Загрузи список → Full Pipeline → Анализ бюджетов
```

### 2. Семантическое ядро
```
Базовые маски → Full Pipeline → Фильтр по частотности → Export
```

### 3. Планирование кампании
```
Все фразы → Full Pipeline → Суммируй по группам → Бюджет готов
```

---

## 📚 Документация

- 🚀 [QUICK_START.md](QUICK_START.md) - Быстрый старт за 5 минут
- 📘 [FULL_PIPELINE_GUIDE.md](FULL_PIPELINE_GUIDE.md) - Полное руководство
- 📙 [UPDATE_INSTRUCTIONS.md](UPDATE_INSTRUCTIONS.md) - Обновление
- 🔧 [GITHUB_WORKFLOW.md](GITHUB_WORKFLOW.md) - Git workflow

---

## 💻 Требования

- Python 3.10+
- Windows 10+ (или Linux/Mac с адаптацией)
- 4GB RAM
- Интернет для Wordstat/Direct

### Зависимости:
```
PySide6==6.8.0.2
playwright==1.48.0
nltk==3.9.1
sqlalchemy==2.0.36
```

---

## 🔧 Установка

```powershell
# 1. Клонирование
git clone https://github.com/websetpro-blip/keyset.git
cd keyset

# 2. Виртуальное окружение (опционально)
python -m venv .venv
.\.venv\Scripts\activate

# 3. Зависимости
pip install -r requirements.txt

# 4. NLTK данные
python -c "import nltk; nltk.download('stopwords')"

# 5. Playwright (если нужен headless браузер)
playwright install chromium

# 6. Запуск
python -m keyset.app.main
```

---

## 🎨 Скриншоты

### Full Pipeline Tab:
```
┌─────────────────────────────────────────────────────────┐
│ 🚀 ЗАПУСТИТЬ FULL PIPELINE                              │
├─────────────────────────────────────────────────────────┤
│ Фразы:                                                  │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ купить телефон                                      │ │
│ │ купить iphone                                       │ │
│ └─────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│ Прогресс: ████████████░░░░░░ 60% (Wordstat: 6/10)      │
├─────────────────────────────────────────────────────────┤
│ Время │ Фраза          │ Частота │ CPC  │ Бюджет │ Груп│
│ 10:30 │ купить телефон │ 15,000  │ 25.5 │ 600    │ купи│
│ 10:31 │ купить iphone  │  8,500  │ 35.0 │ 476    │ купи│
└─────────────────────────────────────────────────────────┘
```

---

## 🤝 Вклад

Проект открыт для вклада! 

### Как помочь:
1. Fork репозитория
2. Создай feature branch
3. Commit изменений
4. Push в branch
5. Создай Pull Request

---

## 📜 Лицензия

Open Source - используй свободно!

---

## 🔗 Ссылки

- **GitHub:** https://github.com/websetpro-blip/keyset
- **Issues:** https://github.com/websetpro-blip/keyset/issues
- **Discussions:** https://github.com/websetpro-blip/keyset/discussions

---

## 📈 История версий

### v2.0 (13.01.2025) - Full Pipeline
- ✅ Добавлен Full Pipeline (Wordstat → Direct → Clustering)
- ✅ NLTK интеграция для группировки
- ✅ WAL режим базы данных
- ✅ Расширенный CSV экспорт

### v1.0 (12.10.2025) - Турбо парсер
- ✅ Турбо-парсер (до 195 фраз/мин)
- ✅ Управление аккаунтами
- ✅ Автологин с CDP

---

## 🙏 Благодарности

- Yandex Wordstat API
- Playwright team
- NLTK contributors
- Qt/PySide6 developers

---

## 📧 Контакты

Вопросы и предложения: [GitHub Issues](https://github.com/websetpro-blip/keyset/issues)

---

**Made with ❤️ for SEO specialists**

🎉 **Удачного парсинга!**

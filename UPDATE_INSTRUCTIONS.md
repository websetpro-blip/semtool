# 🔄 ИНСТРУКЦИЯ ПО ОБНОВЛЕНИЮ SEMTOOL

**Дата:** 13.01.2025  
**Версия:** Turbo Parser Pipeline (файл 41)

---

## ⚠️ ВАЖНО: ПЕРЕЗАПУСТИТЕ GUI ПОСЛЕ ОБНОВЛЕНИЯ!

Python кэширует импортированные модули. После `git pull` необходим **полный перезапуск приложения**.

---

## 📦 ЧТО ОБНОВЛЕНО:

### 1. База данных (core/db.py)
- ✅ Включен WAL режим для конкурентности
- ✅ Добавлены 3 новые таблицы:
  - `frequencies` - результаты Wordstat
  - `forecasts` - прогнозы бюджета Direct
  - `clusters` - кластеризованные данные

### 2. Сервисы парсинга
- ✅ `services/frequency.py` - batch парсинг Wordstat (60-80 масок/мин)
- ✅ `services/direct.py` - прогноз бюджета Direct (100 масок/мин)
- ✅ Автосохранение в БД
- ✅ Rate limiting и обработка ошибок

### 3. Зависимости
- ✅ `requirements.txt` с nltk для кластеризации
- ✅ PySide6, Playwright, SQLAlchemy

---

## 🚀 ПОШАГОВОЕ ОБНОВЛЕНИЕ:

### Шаг 1: Закройте GUI
```powershell
# Закройте окно KeySet
# Убедитесь что процесс Python завершен:
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
```

**ВАЖНО:** Python автоматически обновит скомпилированные файлы (.pyc) 
при следующем запуске, если увидит что исходники (.py) новее!

---

### Шаг 2: Подтяните изменения из GitHub
```powershell
cd C:\AI\yandex\keyset
git pull origin main
```

**Ожидаемый вывод:**
```
Updating 60d439b..c464b8e
Fast-forward
 core/db.py           | 119 ++++++++++++++++++++++++++++++++++++++++++++++++++
 services/frequency.py| 117 ++++++++++++++++++++++++++++++++++++++++++++++
 services/direct.py   | 193 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 requirements.txt     |   5 ++
 4 files changed, 434 insertions(+)
```

---

### Шаг 3: Установите новые зависимости
```powershell
# Если используете venv:
.\.venv\Scripts\activate

# Установка nltk:
python -m pip install nltk==3.9.1

# Скачать данные NLTK (stopwords для русского):
python -c "import nltk; nltk.download('stopwords', quiet=True); print('NLTK data installed')"
```

**Проверка:**
```powershell
python -c "import nltk; from nltk.stem.snowball import SnowballStemmer; print('OK')"
```

---

### Шаг 4: Проверьте обновление базы данных
```powershell
python -c "from core.db import engine, ensure_schema, get_db_connection; ensure_schema(); print('DB schema updated')"
```

**Проверка таблиц:**
```powershell
python -c "from core.db import get_db_connection; conn = get_db_connection().__enter__(); cursor = conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"'); tables = [r[0] for r in cursor.fetchall()]; print('Tables:', tables); conn.close()"
```

**Ожидаемые таблицы:**
- accounts
- tasks
- freq_results
- **frequencies** ← НОВАЯ
- **forecasts** ← НОВАЯ
- **clusters** ← НОВАЯ

**Проверка WAL режима:**
```powershell
python -c "from core.db import get_db_connection; conn = get_db_connection().__enter__(); mode = conn.execute('PRAGMA journal_mode').fetchone()[0]; print(f'Journal mode: {mode}'); conn.close()"
```

Должно быть: `Journal mode: wal`

---

### Шаг 5: Перезапустите GUI
```powershell
python -m keyset.app.main
```

**ИЛИ в Cursor/VS Code:**
```
1. Ctrl+Shift+P → "Python: Restart Language Server"
2. Ctrl+Shift+P → "Developer: Reload Window"
3. F5 или запустите main.py
```

---

## 🎯 КАК ИСПОЛЬЗОВАТЬ НОВЫЙ ФУНКЦИОНАЛ:

### Turbo Parser теперь может:

#### 1. Парсить частотность (Wordstat)
```python
from services.frequency import parse_batch_wordstat
import asyncio

masks = ["купить телефон", "купить iphone"]
results = asyncio.run(parse_batch_wordstat(masks, chunk_size=80, region=225))

# Результат: [{'phrase': 'купить телефон', 'freq': 15000, 'region': 225}, ...]
```

#### 2. Прогнозировать бюджет (Direct)
```python
from services.direct import forecast_batch_direct

freq_results = [{'phrase': 'купить телефон', 'freq': 15000, 'region': 225}]
forecasts = asyncio.run(forecast_batch_direct(freq_results, chunk_size=100))

# Результат: [{'phrase': '...', 'cpc': 25.5, 'impressions': 12000, 'budget': 600}, ...]
```

#### 3. Объединить данные
```python
from services.direct import merge_freq_and_forecast

merged = asyncio.run(merge_freq_and_forecast(freq_results, forecasts))
# Результат: [{'phrase': '...', 'freq': 15000, 'cpc': 25.5, 'budget': 600}, ...]
```

---

## 📊 ПРОВЕРКА РАБОТОСПОСОБНОСТИ:

### Тест 1: Импорт модулей
```powershell
python -c "from services.frequency import parse_batch_wordstat; from services.direct import forecast_batch_direct; print('Services imported OK')"
```

### Тест 2: БД
```powershell
python -c "from core.db import get_db_connection; with get_db_connection() as conn: conn.execute('SELECT * FROM frequencies LIMIT 1'); print('DB OK')"
```

### Тест 3: NLTK
```powershell
python -c "from nltk.stem.snowball import SnowballStemmer; stemmer = SnowballStemmer('russian'); print(stemmer.stem('купить')); print('NLTK OK')"
```

---

## ❌ РЕШЕНИЕ ПРОБЛЕМ:

### Проблема: "ImportError: cannot import name 'get_db_connection'"
**Решение:**
```powershell
# Удалите кэш Python:
Remove-Item -Recurse -Force core/__pycache__
Remove-Item -Recurse -Force services/__pycache__

# Перезапустите Python
```

---

### Проблема: "No module named 'nltk'"
**Решение:**
```powershell
python -m pip install nltk==3.9.1
python -c "import nltk; nltk.download('stopwords')"
```

---

### Проблема: GUI не обновился, старый интерфейс
**Решение:**
```powershell
# 1. Закройте GUI полностью
Get-Process python | Stop-Process -Force

# 2. Git pull еще раз
git pull origin main

# 3. Перезапустите
python -m keyset.app.main

# ПРИМЕЧАНИЕ: Python автоматически обновит кэш (.pyc файлы)
# когда увидит что .py файлы новее. Удалять __pycache__ 
# обычно НЕ НУЖНО!

# ТОЛЬКО если не помогло (очень редко):
Remove-Item -Recurse -Force __pycache__, */__pycache__
```

---

### Проблема: "Table 'frequencies' doesn't exist"
**Решение:**
```powershell
# Принудительно пересоздайте схему:
python -c "from core.db import ensure_schema; ensure_schema(); print('Schema recreated')"

# Проверьте:
python -c "from core.db import get_db_connection; conn = get_db_connection().__enter__(); print(conn.execute('PRAGMA table_info(frequencies)').fetchall())"
```

---

## 📈 СЛЕДУЮЩИЕ ШАГИ:

После успешного обновления:

1. ✅ Запустите GUI - `python -m keyset.app.main`
2. ✅ Перейдите на вкладку **Turbo Parser**
3. ✅ Загрузите тестовый файл с 5-10 фразами
4. ✅ Запустите парсинг
5. ✅ Проверьте что данные сохраняются в БД

---

## 🔗 КОММИТЫ В GITHUB:

- `c464b8e` - feat: add requirements.txt with all dependencies
- `0f556b7` - feat: add full turbo parser pipeline services
- `8d9005d` - feat: add WAL mode and turbo parser tables to database

**Репозиторий:** https://github.com/websetpro-blip/keyset

---

## 📞 ПОДДЕРЖКА:

Если возникли проблемы:
1. Проверьте логи в консоли
2. Убедитесь что git pull выполнен
3. Убедитесь что GUI полностью перезапущен
4. Проверьте что все команды из "ПРОВЕРКА РАБОТОСПОСОБНОСТИ" выполнились без ошибок

**Важно:** Кэширование Python - основная причина "не обновилось". Всегда закрывайте GUI перед git pull!

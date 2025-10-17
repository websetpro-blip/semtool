# 🚀 QUICK START - KeySet Full Pipeline

**За 15 минут до первого запуска!**

---

## ⚡ ШАГ 1: Подготовка окружения (5 мин)

### Windows
```powershell
# Клонирование репозитория
git clone https://github.com/websetpro-blip/keyset.git
cd keyset

# Создание виртуального окружения
python -m venv venv
venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Установка Playwright
playwright install chromium
```

### Linux/macOS
```bash
# Клонирование репозитория
git clone https://github.com/websetpro-blip/keyset.git
cd keyset

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Установка Playwright
playwright install chromium
```

**Ожидается:** ✅ Все пакеты установлены без ошибок

---

## ⚡ ШАГ 2: Установка NLTK для кластеризации (2 мин)

```python
# Запустите в Python или создайте файл setup_nltk.py
import nltk
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Скачать необходимые данные
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('snowball_data')

print('✓ NLTK готов для кластеризации!')
```

**Или одной командой:**
```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('snowball_data'); print('✓ NLTK готов!')"
```

---

## ⚡ ШАГ 3: Настройка конфигурации (3 мин)

### Создайте config.json

```json
{
  "region_id": 213,
  "proxy": {
    "enabled": false,
    "server": "",
    "username": "",
    "password": ""
  },
  "direct_api": {
    "token": "",
    "client_login": ""
  },
  "parsing": {
    "batch_size": 195,
    "delay_range": [2, 5],
    "max_retries": 3
  },
  "clustering": {
    "method": "stem",
    "threshold": 0.7,
    "min_cluster_size": 2
  },
  "export": {
    "formats": ["csv", "xlsx"],
    "encoding": "utf-8-sig",
    "delimiter": ","
  }
}
```

### Основные параметры:
- **region_id**: 213 (Москва), 2 (СПб), 54 (Екатеринбург)
- **proxy.enabled**: false (отключить) или true (включить)
- **batch_size**: до 195 для максимальной скорости

---

## ⚡ ШАГ 4: Подготовка аккаунтов Yandex (2 мин)

### Способ 1: Автологин (рекомендуется)
```bash
python login.py --email your@email.com --password yourpassword
```

### Способ 2: Ручной вход
```bash
python login.py --manual
```

**Результат:** Сохранённые куки в папке `user_data`

---

## ⚡ ШАГ 5: Настройка Direct API (опционально)

### Получение токена:
1. Перейдите: https://oauth.yandex.ru/
2. Зарегистрируйте приложение
3. Получите **OAuth Token**
4. Добавьте в `config.json`:

```json
{
  "direct_api": {
    "token": "YOUR_OAUTH_TOKEN",
    "client_login": "your-login"
  }
}
```

---

## 🔥 ПЕРВЫЙ ЗАПУСК - 3 примера

### Пример 1: Простой парсинг Wordstat

**Создайте файл keywords.txt:**
```
купить телефон
телефон цена
смартфон москва
```

**Запустите парсинг:**
```bash
python main.py --mode wordstat --input keywords.txt --output results/
```

**Результат:** CSV с частотностями по каждому запросу

### Пример 2: Full Pipeline Mode

**Создайте файл masks.txt:**
```
купить [товар]
заказать [товар]
цена [товар]
```

**Запустите полный цикл:**
```bash
python main.py --mode full --input masks.txt --region 213 --output results/
```

**Результат:**
- ✅ Wordstat частотности
- ✅ Direct прогнозы (CPC, клики, показы)
- ✅ Автоматические кластеры
- ✅ XLSX файл со всеми данными

### Пример 3: Кластеризация готовых фраз

**Создайте файл phrases.txt:**
```
купить автомобиль москва
автомобиль купить недорого
машина купить цена
авто купить бу
продажа автомобилей
```

**Запустите кластеризацию:**
```bash
python main.py --mode cluster --input phrases.txt
```

**Результат:** Группировка фраз по семантической близости

---

## 🎯 Быстрые команды

### Только Wordstat (без Direct)
```bash
python main.py --mode wordstat --input keywords.txt
```

### Только Direct прогнозы
```bash
python main.py --mode direct --input keywords.txt
```

### С использованием прокси
```bash
python main.py --mode full --input keywords.txt --proxy "http://user:pass@proxy:8080"
```

### Определённый регион
```bash
python main.py --mode full --input keywords.txt --region 2  # СПб
```

### Экспорт в разные форматы
```bash
python main.py --mode full --input keywords.txt --format csv,xlsx,json
```

---

## 🔧 Настройка для продвинутых

### Batch размер и задержки
```json
{
  "parsing": {
    "batch_size": 150,     // Меньше = безопаснее
    "delay_range": [3, 7], // Больше = безопаснее
    "max_retries": 5       // Больше попыток при ошибках
  }
}
```

### Прокси настройка
```json
{
  "proxy": {
    "enabled": true,
    "server": "http://proxy.example.com:8080",  // HTTP
    "server": "socks5://proxy.example.com:1080", // SOCKS5
    "username": "user",
    "password": "pass",
    "rotate": true  // Автоматическая ротация
  }
}
```

### Кластеризация тонкая настройка
```json
{
  "clustering": {
    "method": "stem",        // stem, ngram, semantic
    "threshold": 0.8,       // Чувствительность группировки
    "min_cluster_size": 3,  // Минимум фраз в кластере
    "language": "russian"   // Язык для стемминга
  }
}
```

---

## 📊 Форматы экспорта

### CSV (UTF-8 с BOM для Excel)
```python
results.to_csv('output.csv', encoding='utf-8-sig', sep=';')
```

### XLSX с форматированием
```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

# Создание книги с стилями
wb = Workbook()
ws = wb.active
ws.title = "KeySet Results"

# Заголовки
headers = ['Keyword', 'Frequency', 'CPC', 'Impressions', 'Clicks', 'Cluster']
for col, header in enumerate(headers, 1):
    cell = ws.cell(1, col, header)
    cell.font = Font(bold=True)
    cell.fill = PatternFill("solid", fgColor="CCCCCC")

wb.save('output.xlsx')
```

### JSON для API интеграций
```json
{
  "keywords": [
    {
      "phrase": "купить телефон",
      "frequency": 15000,
      "cpc": 25.5,
      "impressions": 120000,
      "clicks": 3000,
      "cluster": "покупка телефонов"
    }
  ],
  "summary": {
    "total_keywords": 100,
    "total_frequency": 500000,
    "avg_cpc": 18.5
  }
}
```

---

## ⚠️ Важные моменты

### Лимиты Yandex
- **Wordstat**: ~200 запросов/минуту
- **Direct API**: 10,000 запросов/день
- **Captcha**: решается автоматически

### Если что-то не работает
1. **Проверьте интернет соединение**
2. **Обновите Playwright**: `playwright install chromium`
3. **Перезапустите Python окружение**
4. **Проверьте логи в папке `logs/`**

### Типичные ошибки
- `ModuleNotFoundError`: не активировано venv
- `TimeoutError`: проблемы с сетью или прокси
- `CaptchaError`: нужна ротация аккаунтов

---

## 🎓 Дальнейшее изучение

- 📚 **[README.md](README.md)** — полная документация
- 📖 **[FULL_PIPELINE_GUIDE.md](FULL_PIPELINE_GUIDE.md)** — детальный гайд
- 🔧 **[UPDATE_INSTRUCTIONS.md](UPDATE_INSTRUCTIONS.md)** — инструкции по обновлению
- 💻 **[GITHUB_WORKFLOW.md](GITHUB_WORKFLOW.md)** — для разработчиков

---

## 🆘 Поддержка

- **Issues**: https://github.com/websetpro-blip/keyset/issues
- **Discussions**: https://github.com/websetpro-blip/keyset/discussions
- **Email**: support@example.com (если указан)

---

**🎉 Готово! Теперь вы можете запускать полный pipeline KeySet!**

**Удачного парсинга! 🚀**

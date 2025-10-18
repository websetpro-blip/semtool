# рџљЂ QUICK START - KeySet Full Pipeline

**Р—Р° 15 РјРёРЅСѓС‚ РґРѕ РїРµСЂРІРѕРіРѕ Р·Р°РїСѓСЃРєР°!**

---

## вљЎ РЁРђР“ 1: РџРѕРґРіРѕС‚РѕРІРєР° РѕРєСЂСѓР¶РµРЅРёСЏ (5 РјРёРЅ)

### Windows
```powershell
# РљР»РѕРЅРёСЂРѕРІР°РЅРёРµ СЂРµРїРѕР·РёС‚РѕСЂРёСЏ
git clone https://github.com/websetpro-blip/keyset.git
cd keyset

# РЎРѕР·РґР°РЅРёРµ РІРёСЂС‚СѓР°Р»СЊРЅРѕРіРѕ РѕРєСЂСѓР¶РµРЅРёСЏ
python -m venv venv
venv\Scripts\activate

# РЈСЃС‚Р°РЅРѕРІРєР° Р·Р°РІРёСЃРёРјРѕСЃС‚РµР№
pip install -r requirements.txt

# РЈСЃС‚Р°РЅРѕРІРєР° Playwright
playwright install chromium
```

### Linux/macOS
```bash
# РљР»РѕРЅРёСЂРѕРІР°РЅРёРµ СЂРµРїРѕР·РёС‚РѕСЂРёСЏ
git clone https://github.com/websetpro-blip/keyset.git
cd keyset

# РЎРѕР·РґР°РЅРёРµ РІРёСЂС‚СѓР°Р»СЊРЅРѕРіРѕ РѕРєСЂСѓР¶РµРЅРёСЏ
python3 -m venv venv
source venv/bin/activate

# РЈСЃС‚Р°РЅРѕРІРєР° Р·Р°РІРёСЃРёРјРѕСЃС‚РµР№
pip install -r requirements.txt

# РЈСЃС‚Р°РЅРѕРІРєР° Playwright
playwright install chromium
```

**РћР¶РёРґР°РµС‚СЃСЏ:** вњ… Р’СЃРµ РїР°РєРµС‚С‹ СѓСЃС‚Р°РЅРѕРІР»РµРЅС‹ Р±РµР· РѕС€РёР±РѕРє

---

## вљЎ РЁРђР“ 2: РЈСЃС‚Р°РЅРѕРІРєР° NLTK РґР»СЏ РєР»Р°СЃС‚РµСЂРёР·Р°С†РёРё (2 РјРёРЅ)

```python
# Р—Р°РїСѓСЃС‚РёС‚Рµ РІ Python РёР»Рё СЃРѕР·РґР°Р№С‚Рµ С„Р°Р№Р» setup_nltk.py
import nltk
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# РЎРєР°С‡Р°С‚СЊ РЅРµРѕР±С…РѕРґРёРјС‹Рµ РґР°РЅРЅС‹Рµ
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('snowball_data')

print('вњ“ NLTK РіРѕС‚РѕРІ РґР»СЏ РєР»Р°СЃС‚РµСЂРёР·Р°С†РёРё!')
```

**РР»Рё РѕРґРЅРѕР№ РєРѕРјР°РЅРґРѕР№:**
```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('snowball_data'); print('вњ“ NLTK РіРѕС‚РѕРІ!')"
```

---

## вљЎ РЁРђР“ 3: РќР°СЃС‚СЂРѕР№РєР° РєРѕРЅС„РёРіСѓСЂР°С†РёРё (3 РјРёРЅ)

### РЎРѕР·РґР°Р№С‚Рµ config.json

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

### РћСЃРЅРѕРІРЅС‹Рµ РїР°СЂР°РјРµС‚СЂС‹:
- **region_id**: 213 (РњРѕСЃРєРІР°), 2 (РЎРџР±), 54 (Р•РєР°С‚РµСЂРёРЅР±СѓСЂРі)
- **proxy.enabled**: false (РѕС‚РєР»СЋС‡РёС‚СЊ) РёР»Рё true (РІРєР»СЋС‡РёС‚СЊ)
- **batch_size**: РґРѕ 195 РґР»СЏ РјР°РєСЃРёРјР°Р»СЊРЅРѕР№ СЃРєРѕСЂРѕСЃС‚Рё

---

## вљЎ РЁРђР“ 4: РџРѕРґРіРѕС‚РѕРІРєР° Р°РєРєР°СѓРЅС‚РѕРІ Yandex (2 РјРёРЅ)

### РЎРїРѕСЃРѕР± 1: РђРІС‚РѕР»РѕРіРёРЅ (СЂРµРєРѕРјРµРЅРґСѓРµС‚СЃСЏ)
```bash
python login.py --email your@email.com --password yourpassword
```

### РЎРїРѕСЃРѕР± 2: Р СѓС‡РЅРѕР№ РІС…РѕРґ
```bash
python login.py --manual
```

**Р РµР·СѓР»СЊС‚Р°С‚:** РЎРѕС…СЂР°РЅС‘РЅРЅС‹Рµ РєСѓРєРё РІ РїР°РїРєРµ `user_data`

---

## вљЎ РЁРђР“ 5: РќР°СЃС‚СЂРѕР№РєР° Direct API (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ)

### РџРѕР»СѓС‡РµРЅРёРµ С‚РѕРєРµРЅР°:
1. РџРµСЂРµР№РґРёС‚Рµ: https://oauth.yandex.ru/
2. Р—Р°СЂРµРіРёСЃС‚СЂРёСЂСѓР№С‚Рµ РїСЂРёР»РѕР¶РµРЅРёРµ
3. РџРѕР»СѓС‡РёС‚Рµ **OAuth Token**
4. Р”РѕР±Р°РІСЊС‚Рµ РІ `config.json`:

```json
{
  "direct_api": {
    "token": "YOUR_OAUTH_TOKEN",
    "client_login": "your-login"
  }
}
```

---

## рџ”Ґ РџР•Р Р’Р«Р™ Р—РђРџРЈРЎРљ - 3 РїСЂРёРјРµСЂР°

### РџСЂРёРјРµСЂ 1: РџСЂРѕСЃС‚РѕР№ РїР°СЂСЃРёРЅРі Wordstat

**РЎРѕР·РґР°Р№С‚Рµ С„Р°Р№Р» keywords.txt:**
```
РєСѓРїРёС‚СЊ С‚РµР»РµС„РѕРЅ
С‚РµР»РµС„РѕРЅ С†РµРЅР°
СЃРјР°СЂС‚С„РѕРЅ РјРѕСЃРєРІР°
```

**Р—Р°РїСѓСЃС‚РёС‚Рµ РїР°СЂСЃРёРЅРі:**
```bash
python main.py --mode wordstat --input keywords.txt --output results/
```

**Р РµР·СѓР»СЊС‚Р°С‚:** CSV СЃ С‡Р°СЃС‚РѕС‚РЅРѕСЃС‚СЏРјРё РїРѕ РєР°Р¶РґРѕРјСѓ Р·Р°РїСЂРѕСЃСѓ

### РџСЂРёРјРµСЂ 2: Full Pipeline Mode

**РЎРѕР·РґР°Р№С‚Рµ С„Р°Р№Р» masks.txt:**
```
РєСѓРїРёС‚СЊ [С‚РѕРІР°СЂ]
Р·Р°РєР°Р·Р°С‚СЊ [С‚РѕРІР°СЂ]
С†РµРЅР° [С‚РѕРІР°СЂ]
```

**Р—Р°РїСѓСЃС‚РёС‚Рµ РїРѕР»РЅС‹Р№ С†РёРєР»:**
```bash
python main.py --mode full --input masks.txt --region 213 --output results/
```

**Р РµР·СѓР»СЊС‚Р°С‚:**
- вњ… Wordstat С‡Р°СЃС‚РѕС‚РЅРѕСЃС‚Рё
- вњ… Direct РїСЂРѕРіРЅРѕР·С‹ (CPC, РєР»РёРєРё, РїРѕРєР°Р·С‹)
- вњ… РђРІС‚РѕРјР°С‚РёС‡РµСЃРєРёРµ РєР»Р°СЃС‚РµСЂС‹
- вњ… XLSX С„Р°Р№Р» СЃРѕ РІСЃРµРјРё РґР°РЅРЅС‹РјРё

### РџСЂРёРјРµСЂ 3: РљР»Р°СЃС‚РµСЂРёР·Р°С†РёСЏ РіРѕС‚РѕРІС‹С… С„СЂР°Р·

**РЎРѕР·РґР°Р№С‚Рµ С„Р°Р№Р» phrases.txt:**
```
РєСѓРїРёС‚СЊ Р°РІС‚РѕРјРѕР±РёР»СЊ РјРѕСЃРєРІР°
Р°РІС‚РѕРјРѕР±РёР»СЊ РєСѓРїРёС‚СЊ РЅРµРґРѕСЂРѕРіРѕ
РјР°С€РёРЅР° РєСѓРїРёС‚СЊ С†РµРЅР°
Р°РІС‚Рѕ РєСѓРїРёС‚СЊ Р±Сѓ
РїСЂРѕРґР°Р¶Р° Р°РІС‚РѕРјРѕР±РёР»РµР№
```

**Р—Р°РїСѓСЃС‚РёС‚Рµ РєР»Р°СЃС‚РµСЂРёР·Р°С†РёСЋ:**
```bash
python main.py --mode cluster --input phrases.txt
```

**Р РµР·СѓР»СЊС‚Р°С‚:** Р“СЂСѓРїРїРёСЂРѕРІРєР° С„СЂР°Р· РїРѕ СЃРµРјР°РЅС‚РёС‡РµСЃРєРѕР№ Р±Р»РёР·РѕСЃС‚Рё

---

## рџЋЇ Р‘С‹СЃС‚СЂС‹Рµ РєРѕРјР°РЅРґС‹

### РўРѕР»СЊРєРѕ Wordstat (Р±РµР· Direct)
```bash
python main.py --mode wordstat --input keywords.txt
```

### РўРѕР»СЊРєРѕ Direct РїСЂРѕРіРЅРѕР·С‹
```bash
python main.py --mode direct --input keywords.txt
```

### РЎ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёРµРј РїСЂРѕРєСЃРё
```bash
python main.py --mode full --input keywords.txt --proxy "http://user:pass@proxy:8080"
```

### РћРїСЂРµРґРµР»С‘РЅРЅС‹Р№ СЂРµРіРёРѕРЅ
```bash
python main.py --mode full --input keywords.txt --region 2  # РЎРџР±
```

### Р­РєСЃРїРѕСЂС‚ РІ СЂР°Р·РЅС‹Рµ С„РѕСЂРјР°С‚С‹
```bash
python main.py --mode full --input keywords.txt --format csv,xlsx,json
```

---

## рџ”§ РќР°СЃС‚СЂРѕР№РєР° РґР»СЏ РїСЂРѕРґРІРёРЅСѓС‚С‹С…

### Batch СЂР°Р·РјРµСЂ Рё Р·Р°РґРµСЂР¶РєРё
```json
{
  "parsing": {
    "batch_size": 150,     // РњРµРЅСЊС€Рµ = Р±РµР·РѕРїР°СЃРЅРµРµ
    "delay_range": [3, 7], // Р‘РѕР»СЊС€Рµ = Р±РµР·РѕРїР°СЃРЅРµРµ
    "max_retries": 5       // Р‘РѕР»СЊС€Рµ РїРѕРїС‹С‚РѕРє РїСЂРё РѕС€РёР±РєР°С…
  }
}
```

### РџСЂРѕРєСЃРё РЅР°СЃС‚СЂРѕР№РєР°
```json
{
  "proxy": {
    "enabled": true,
    "server": "http://proxy.example.com:8080",  // HTTP
    "server": "socks5://proxy.example.com:1080", // SOCKS5
    "username": "user",
    "password": "pass",
    "rotate": true  // РђРІС‚РѕРјР°С‚РёС‡РµСЃРєР°СЏ СЂРѕС‚Р°С†РёСЏ
  }
}
```

### РљР»Р°СЃС‚РµСЂРёР·Р°С†РёСЏ С‚РѕРЅРєР°СЏ РЅР°СЃС‚СЂРѕР№РєР°
```json
{
  "clustering": {
    "method": "stem",        // stem, ngram, semantic
    "threshold": 0.8,       // Р§СѓРІСЃС‚РІРёС‚РµР»СЊРЅРѕСЃС‚СЊ РіСЂСѓРїРїРёСЂРѕРІРєРё
    "min_cluster_size": 3,  // РњРёРЅРёРјСѓРј С„СЂР°Р· РІ РєР»Р°СЃС‚РµСЂРµ
    "language": "russian"   // РЇР·С‹Рє РґР»СЏ СЃС‚РµРјРјРёРЅРіР°
  }
}
```

---

## рџ“Љ Р¤РѕСЂРјР°С‚С‹ СЌРєСЃРїРѕСЂС‚Р°

### CSV (UTF-8 СЃ BOM РґР»СЏ Excel)
```python
results.to_csv('output.csv', encoding='utf-8-sig', sep=';')
```

### XLSX СЃ С„РѕСЂРјР°С‚РёСЂРѕРІР°РЅРёРµРј
```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

# РЎРѕР·РґР°РЅРёРµ РєРЅРёРіРё СЃ СЃС‚РёР»СЏРјРё
wb = Workbook()
ws = wb.active
ws.title = "KeySet Results"

# Р—Р°РіРѕР»РѕРІРєРё
headers = ['Keyword', 'Frequency', 'CPC', 'Impressions', 'Clicks', 'Cluster']
for col, header in enumerate(headers, 1):
    cell = ws.cell(1, col, header)
    cell.font = Font(bold=True)
    cell.fill = PatternFill("solid", fgColor="CCCCCC")

wb.save('output.xlsx')
```

### JSON РґР»СЏ API РёРЅС‚РµРіСЂР°С†РёР№
```json
{
  "keywords": [
    {
      "phrase": "РєСѓРїРёС‚СЊ С‚РµР»РµС„РѕРЅ",
      "frequency": 15000,
      "cpc": 25.5,
      "impressions": 120000,
      "clicks": 3000,
      "cluster": "РїРѕРєСѓРїРєР° С‚РµР»РµС„РѕРЅРѕРІ"
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

## вљ пёЏ Р’Р°Р¶РЅС‹Рµ РјРѕРјРµРЅС‚С‹

### Р›РёРјРёС‚С‹ Yandex
- **Wordstat**: ~200 Р·Р°РїСЂРѕСЃРѕРІ/РјРёРЅСѓС‚Сѓ
- **Direct API**: 10,000 Р·Р°РїСЂРѕСЃРѕРІ/РґРµРЅСЊ
- **Captcha**: СЂРµС€Р°РµС‚СЃСЏ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё

### Р•СЃР»Рё С‡С‚Рѕ-С‚Рѕ РЅРµ СЂР°Р±РѕС‚Р°РµС‚
1. **РџСЂРѕРІРµСЂСЊС‚Рµ РёРЅС‚РµСЂРЅРµС‚ СЃРѕРµРґРёРЅРµРЅРёРµ**
2. **РћР±РЅРѕРІРёС‚Рµ Playwright**: `playwright install chromium`
3. **РџРµСЂРµР·Р°РїСѓСЃС‚РёС‚Рµ Python РѕРєСЂСѓР¶РµРЅРёРµ**
4. **РџСЂРѕРІРµСЂСЊС‚Рµ Р»РѕРіРё РІ РїР°РїРєРµ `logs/`**

### РўРёРїРёС‡РЅС‹Рµ РѕС€РёР±РєРё
- `ModuleNotFoundError`: РЅРµ Р°РєС‚РёРІРёСЂРѕРІР°РЅРѕ venv
- `TimeoutError`: РїСЂРѕР±Р»РµРјС‹ СЃ СЃРµС‚СЊСЋ РёР»Рё РїСЂРѕРєСЃРё
- `CaptchaError`: РЅСѓР¶РЅР° СЂРѕС‚Р°С†РёСЏ Р°РєРєР°СѓРЅС‚РѕРІ

---

## рџЋ“ Р”Р°Р»СЊРЅРµР№С€РµРµ РёР·СѓС‡РµРЅРёРµ

- рџ“љ **[README.md](README.md)** вЂ” РїРѕР»РЅР°СЏ РґРѕРєСѓРјРµРЅС‚Р°С†РёСЏ
- рџ“– **[FULL_PIPELINE_GUIDE.md](FULL_PIPELINE_GUIDE.md)** вЂ” РґРµС‚Р°Р»СЊРЅС‹Р№ РіР°Р№Рґ
- рџ”§ **[UPDATE_INSTRUCTIONS.md](UPDATE_INSTRUCTIONS.md)** вЂ” РёРЅСЃС‚СЂСѓРєС†РёРё РїРѕ РѕР±РЅРѕРІР»РµРЅРёСЋ
- рџ’» **[GITHUB_WORKFLOW.md](GITHUB_WORKFLOW.md)** вЂ” РґР»СЏ СЂР°Р·СЂР°Р±РѕС‚С‡РёРєРѕРІ

---

## рџ† РџРѕРґРґРµСЂР¶РєР°

- **Issues**: https://github.com/websetpro-blip/keyset/issues
- **Discussions**: https://github.com/websetpro-blip/keyset/discussions
- **Email**: support@example.com (РµСЃР»Рё СѓРєР°Р·Р°РЅ)

---

**рџЋ‰ Р“РѕС‚РѕРІРѕ! РўРµРїРµСЂСЊ РІС‹ РјРѕР¶РµС‚Рµ Р·Р°РїСѓСЃРєР°С‚СЊ РїРѕР»РЅС‹Р№ pipeline KeySet!**

**РЈРґР°С‡РЅРѕРіРѕ РїР°СЂСЃРёРЅРіР°! рџљЂ**
**Готово! Теперь можно запускать GUI KeySet.**
## Запуск GUI (Comet)

```powershell
python -m keyset.app.main
# или
python run_keyset.pyw
```

- Верхняя панель: Частотка, Вглубь (левая/правая), Прогноз бюджета, Гео, Минусовка, Стоп-слова, Экспорт, Аналитика.
- Вкладки: Аккаунты / Парсинг / Маски. Кнопка «Перенести в Парсинг» на вкладке Маски отправляет фразы сразу в парсинг.
- История задач находится внизу; обновление списка аккаунтов обновляет выпадающий список профилей.

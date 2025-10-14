# services/forecast_ui.py
from __future__ import annotations
import asyncio, re, json
from typing import Iterable, Dict, Any, List, Optional
from playwright.async_api import Page, BrowserContext

# ------ Локаторы (робастные + фолбэки) ------
LOC_FORECAST_ENTRY = [
    "text=Прогноз бюджета",
    "role=link[name='Прогноз бюджета']",
    "role=menuitem[name='Прогноз бюджета']",
    "text=Budget forecast",
]
LOC_REGION_OPEN = [
    "role=button[name=/Регионы|Регионы показов|Изменить регионы/i]",
    "text=Регионы показов",
    "text=Регионы",
    "text=Regions",
]
LOC_REGION_MODAL_OK = [
    "role=button[name=/Готово|Сохранить|Применить/i]",
    "text=/Готово|Сохранить|Применить/i"
]
LOC_KW_INPUT = [
    "textarea[placeholder*='ключев' i]",
    "textarea[aria-label*='ключев' i]",
    "div[contenteditable='true']"
]
LOC_CALCULATE = [
    "role=button[name=/Рассчитать|Посчитать|Получить прогноз/i]",
    "text=/Рассчитать|Посчитать|Получить прогноз/i"
]

def _first(page: Page, variants: List[str]):
    for sel in variants:
        loc = page.locator(sel)
        if loc and loc.count() >= 0:
            return loc.first
    raise RuntimeError(f"Selector not found among: {variants}")

async def open_budget_forecast(page: Page):
    # Мы уже в https://direct.yandex.ru/ с активной сессией (storage_state профиля)
    # 1) Попробовать найти пункт меню
    try:
        await _first(page, LOC_FORECAST_ENTRY).click(timeout=10_000)
    except:
        # Фолбэк: иногда инструмент доступен по прямой ссылке
        for url in [
            "https://direct.yandex.ru/registered/main.pl?cmd=BudgetForecast",
            "https://direct.yandex.ru/forecast",
        ]:
            try:
                await page.goto(url, timeout=20_000)
                break
            except: 
                pass
    # Дождаться загрузки формы
    await _first(page, LOC_CALCULATE).wait_for(timeout=20_000)

async def set_regions(page: Page, region_names_or_ids: List[str|int]):
    # Открыть окно выбора регионов
    await _first(page, LOC_REGION_OPEN).click(timeout=10_000)
    # В модальном древе ищем элементы
    for r in region_names_or_ids:
        patt = str(r)
        node = page.locator("[role='treeitem']", has_text=re.compile(patt))
        # чекбокс внутри узла
        cb = node.locator("input[type='checkbox'], div[role='checkbox']")
        if await cb.count() == 0:
            # попытка раскрыть родителя
            await node.click()
            cb = node.locator("input[type='checkbox'], div[role='checkbox']")
        try:
            await cb.first.check(timeout=3_000)
        except:
            try:
                await cb.first.click()
            except:
                await node.press("Space")
    # Применить
    await _first(page, LOC_REGION_MODAL_OK).click(timeout=10_000)

async def fill_phrases(page: Page, phrases: List[str]):
    # Поле может быть textarea или contenteditable
    box = _first(page, LOC_KW_INPUT)
    try:
        await box.fill("\n".join(phrases))
    except:
        await box.click()
        for ph in phrases:
            await page.keyboard.type(ph)
            await page.keyboard.press("Enter")

async def click_calculate(page: Page):
    await _first(page, LOC_CALCULATE).click(timeout=10_000)

def _extract_from_json(jd: Any) -> List[Dict[str, Any]]:
    """
    Вытаскиваем [{phrase, shows, clicks, cost, cpc}] из JSON «Прогноза бюджета».
    """
    items = []
    
    def find_phrases(d):
        if isinstance(d, dict):
            if "Phrases" in d and isinstance(d["Phrases"], list): 
                return d["Phrases"]
            for v in d.values():
                x = find_phrases(v)
                if x is not None: 
                    return x
        if isinstance(d, list):
            for e in d:
                x = find_phrases(e)
                if x is not None: 
                    return x
        return None

    arr = find_phrases(jd) or []
    for it in arr:
        phrase = it.get("Phrase") or it.get("Keyword") or it.get("Text") or ""
        shows  = it.get("Shows") or it.get("Impressions") or 0
        clicks = it.get("Clicks") or 0
        cost   = it.get("Sum") or it.get("Cost") or it.get("Price") or 0.0
        cpc    = (float(cost) / max(1, float(clicks))) if clicks else 0.0
        items.append({
            "phrase": phrase, 
            "shows": int(shows), 
            "clicks": int(clicks), 
            "cost": float(cost), 
            "cpc": round(cpc, 2)
        })
    
    # Фолбэк: если массив не найден, попробуем Common‑метрики
    if not items and isinstance(jd, dict):
        common = jd.get("Common") or {}
        if common:
            clicks = common.get("Clicks") or 0
            items.append({
                "phrase": "__TOTAL__", 
                "shows": int(common.get("Shows") or 0), 
                "clicks": int(clicks),
                "cost": float(common.get("Sum") or 0.0), 
                "cpc": round((common.get("Sum") or 0.0)/max(1,clicks), 2)
            })
    return items

async def wait_forecast_json(page: Page, timeout_ms=45_000) -> List[Dict[str, Any]]:
    """
    Ждём XHR JSON с ответом «Прогноза бюджета».
    """
    def _is_json_forecast(resp):
        ct = (resp.headers.get("content-type", "") or "").lower()
        if "application/json" not in ct: 
            return False
        u = (resp.url or "").lower()
        return ("forecast" in u) or ("live/v4" in u) or ("create" in u and "forecast" in u) or ("getforecast" in u)
    
    resp = await page.wait_for_response(_is_json_forecast, timeout=timeout_ms)
    try:
        jd = await resp.json()
    except:
        txt = await resp.text()
        jd = json.loads(txt) if txt.strip().startswith("{") else {}
    return _extract_from_json(jd)

async def forecast_batch(context: BrowserContext, phrases: List[str], region_ids: List[int]) -> List[Dict[str, Any]]:
    """
    Полный цикл: открыть инструмент, проставить регионы, вставить фразы, рассчитать.
    """
    page = await context.new_page()
    await page.goto("https://direct.yandex.ru/", timeout=60_000)
    await open_budget_forecast(page)
    
    if region_ids:
        await set_regions(page, [str(i) for i in region_ids])
    
    out = []
    CHUNK = 80
    for i in range(0, len(phrases), CHUNK):
        chunk = phrases[i:i+CHUNK]
        await fill_phrases(page, chunk)
        await click_calculate(page)
        data = await wait_forecast_json(page)
        out.extend(data)
        await page.wait_for_timeout(300)
    
    await page.close()
    return out

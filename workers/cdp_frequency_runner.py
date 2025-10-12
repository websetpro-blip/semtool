"""
Улучшенный воркер частотности через CDP attach + перехват CSV/XHR
Идеи взяты из GPT Pro deep research + наш существующий код
"""
from __future__ import annotations

import asyncio
import json
import re
import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from playwright.async_api import async_playwright, Page, Response
import requests

from ..core.db import SessionLocal
from ..core.models import Account, FrequencyResult


class CDPFrequencyParser:
    """
    Парсер через CDP attach к уже запущенному Chrome
    
    Workflow:
    1. Запускаем Chrome с --remote-debugging-port=9222 ВРУЧНУЮ
    2. Логинимся в Wordstat ВРУЧНУЮ в этом Chrome
    3. Этот парсер подключается к тому же Chrome через CDP
    4. Перехватывает CSV/XHR ответы
    5. Извлекает URL экспорта и реплеит его через HTTP (БЕЗ UI!)
    """
    
    def __init__(self, cdp_url: str = "http://localhost:9222"):
        self.cdp_url = cdp_url
        self.captured_data = []
        self.export_url_template = None
        self.session: Optional[requests.Session] = None
    
    async def init_connection(self):
        """Подключаемся к уже запущенному Chrome"""
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(self.cdp_url)
            context = browser.contexts[0] if browser.contexts else None
            
            if not context:
                raise RuntimeError("No context found. Is Chrome running with --remote-debugging-port?")
            
            return browser, context
    
    async def capture_export_url(self, page: Page, masks_sample: list[str]):
        """
        Ловим URL экспорта CSV при первом запросе
        Потом будем реплеить этот URL для всех масок
        """
        
        captured_csv_url = None
        
        async def on_response(response: Response):
            nonlocal captured_csv_url
            url = response.url
            content_type = response.headers.get("content-type", "")
            
            # Ловим CSV от Wordstat
            if "wordstat" in url and ("csv" in content_type or "export" in url or "download" in url):
                print(f"[CDP] Поймал CSV URL: {url}")
                captured_csv_url = url
                
                # Сохраняем тело для анализа
                try:
                    body = await response.body()
                    self.captured_data.append({
                        "url": url,
                        "type": "csv",
                        "body": body.decode("utf-8", "ignore")
                    })
                except Exception as e:
                    print(f"[CDP] Ошибка чтения CSV: {e}")
        
        page.on("response", on_response)
        
        # Пробуем первую маску и жмём "Скачать"
        if masks_sample:
            mask = masks_sample[0]
            await page.goto(f"https://wordstat.yandex.ru/?words={quote(mask)}&regions=225")
            await asyncio.sleep(2)
            
            # Ищем кнопку "Скачать"
            download_btn = page.locator('text="Скачать"')
            try:
                if await download_btn.count() > 0:
                    await download_btn.first.click(timeout=3000)
                    await asyncio.sleep(2)  # Даём время на запрос
            except Exception as e:
                print(f"[CDP] Кнопка Скачать не найдена: {e}")
        
        return captured_csv_url
    
    def build_http_session(self, context_cookies):
        """
        Создаём HTTP сессию с теми же cookies что в браузере
        Для реплея запросов БЕЗ UI
        """
        session = requests.Session()
        
        for cookie in context_cookies:
            session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain", "yandex.ru"),
                path=cookie.get("path", "/")
            )
        
        session.headers.update({
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://wordstat.yandex.ru/"
        })
        
        return session
    
    def replay_export_http(self, masks: list[str], export_url_template: str, region: int = 225) -> list[dict]:
        """
        Реплеим запрос экспорта для каждой маски через HTTP
        БЕЗ браузера! В 10 раз быстрее!
        """
        import time
        import random
        
        if not self.session:
            raise RuntimeError("HTTP session not initialized")
        
        results = []
        
        for idx, mask in enumerate(masks, 1):
            # Подставляем маску в URL
            url = export_url_template.replace("{q}", quote(mask))
            url = re.sub(r'words=[^&]*', f'words={quote(mask)}', url)
            
            try:
                resp = self.session.get(url, timeout=30)
                
                if resp.status_code == 200 and "csv" in resp.headers.get("content-type", ""):
                    # Парсим CSV
                    freq = self._parse_csv_response(resp.text, mask)
                    if freq:
                        results.append({
                            "mask": mask,
                            "freq": freq,
                            "region": region
                        })
                        print(f"[HTTP] [{idx}/{len(masks)}] {mask}: {freq:,}")
                    else:
                        print(f"[HTTP] [{idx}/{len(masks)}] {mask}: частота не найдена в CSV")
                else:
                    print(f"[HTTP] [{idx}/{len(masks)}] {mask}: ошибка {resp.status_code}")
                
                # Пауза между запросами (синхронный sleep!)
                time.sleep(random.uniform(2.0, 3.5))
            
            except Exception as e:
                print(f"[HTTP] [{idx}/{len(masks)}] {mask}: {e}")
        
        return results
    
    async def _parse_frequency_from_page(self, page: Page, mask: str) -> Optional[int]:
        """
        ПРАВИЛЬНЫЙ парсинг частоты со страницы Wordstat
        """
        try:
            # Метод 1: Ищем в таблице
            tables = await page.locator('table').all()
            
            if tables:
                table = tables[0]  # Первая таблица = результаты
                rows = await table.locator('tr').all()
                
                mask_lower = mask.lower().strip()
                
                for row in rows:
                    text = await row.inner_text()
                    
                    # Ищем строку с нашей маской
                    if mask_lower in text.lower():
                        # Формат: "маска\t827 960"
                        parts = text.split('\t')
                        if len(parts) >= 2:
                            # Берём второй элемент (частота)
                            freq_str = parts[1].strip().replace(' ', '').replace('\xa0', '').replace(',', '')
                            
                            # Может быть несколько чисел, берём первое
                            numbers = re.findall(r'\d+', freq_str)
                            if numbers:
                                return int(numbers[0])
            
            # Метод 2: Fallback - ищем в тексте
            text = await page.inner_text("body")
            pattern = rf'{re.escape(mask)}[:\s]+(\d[\d\s]+\d{{3}})'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                freq_str = match.group(1).replace(' ', '').replace('\xa0', '').replace(',', '')
                return int(freq_str)
        
        except Exception as e:
            print(f"[Parse Error] {mask}: {e}")
        
        return None
    
    def _parse_csv_response(self, csv_text: str, mask: str) -> Optional[int]:
        """Парсит CSV от Wordstat и извлекает частоту"""
        try:
            reader = csv.reader(io.StringIO(csv_text), delimiter=";")
            mask_norm = mask.lower().strip()
            
            for row in reader:
                if not row or len(row) < 2:
                    continue
                
                phrase = row[0].lower().strip()
                
                # Пропускаем заголовки
                if "ключев" in phrase or "фраз" in phrase:
                    continue
                
                # Ищем точное совпадение с маской
                if phrase == mask_norm:
                    # Частота обычно во 2-й колонке
                    freq_str = row[1].replace(" ", "").replace(",", "").replace('\xa0', '')
                    if freq_str.isdigit():
                        return int(freq_str)
            
            # Если точного совпадения нет, берём первую строку с числом
            reader = csv.reader(io.StringIO(csv_text), delimiter=";")
            for row in reader:
                if len(row) >= 2:
                    freq_str = row[1].replace(" ", "").replace(",", "").replace('\xa0', '')
                    if freq_str.isdigit():
                        return int(freq_str)
        
        except Exception:
            pass
        
        return None


async def parse_with_cdp(
    account_id: int,
    masks: list[str],
    region: int = 225,
    cdp_url: str = "http://localhost:9222",
    on_progress: callable = None
) -> dict:
    """
    Главная функция - парсинг через CDP
    
    Args:
        account_id: ID аккаунта
        masks: Список масок
        region: Регион
        cdp_url: URL CDP (порт Chrome)
        on_progress: Callback прогресса
    
    Returns:
        Статистика парсинга
    """
    
    # Записываем маски в БД
    with SessionLocal() as session:
        for mask in masks:
            mask_norm = mask.strip()
            if not mask_norm:
                continue
            
            existing = session.query(FrequencyResult).filter(
                FrequencyResult.mask == mask_norm,
                FrequencyResult.region == region
            ).first()
            
            if not existing:
                session.add(FrequencyResult(
                    mask=mask_norm,
                    region=region,
                    status='queued'
                ))
        session.commit()
    
    parser = CDPFrequencyParser(cdp_url)
    
    async with async_playwright() as p:
        # Подключаемся к запущенному Chrome
        browser = await p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Шаг 1: Ловим URL экспорта на первой маске
        print("[CDP] Захват URL экспорта...")
        export_url = await parser.capture_export_url(page, masks[:1])
        
        if not export_url:
            print("[CDP] Не удалось поймать URL экспорта. Парсим через UI...")
            # Fallback на обычный парсинг через UI
            from .session_frequency_runner import parse_frequency_with_session
            return await parse_frequency_with_session(account_id, masks, region, False, on_progress)
        
        print(f"[CDP] URL экспорта: {export_url}")
        
        # Шаг 2: Строим HTTP сессию с теми же cookies
        cookies = await context.cookies()
        parser.session = parser.build_http_session(cookies)
        
        await browser.close()
    
    # Шаг 3: Реплеим через HTTP (БЕЗ браузера!)
    print(f"[HTTP] Начинаю реплей для {len(masks)} масок...")
    results = parser.replay_export_http(masks, export_url, region)
    
    # Шаг 4: Записываем в БД
    stats = {"success": 0, "failed": 0}
    
    for result in results:
        try:
            with SessionLocal() as session:
                freq_result = session.query(FrequencyResult).filter(
                    FrequencyResult.mask == result["mask"],
                    FrequencyResult.region == region
                ).first()
                
                if freq_result:
                    freq_result.status = "ok"
                    freq_result.freq_total = result["freq"]
                    freq_result.updated_at = datetime.utcnow()
                    session.commit()
                    stats["success"] += 1
                    
                    if on_progress:
                        on_progress(result["mask"], result["freq"], stats["success"], len(masks))
        except Exception as e:
            print(f"[DB] Ошибка записи {result['mask']}: {e}")
            stats["failed"] += 1
    
    # Обновляем last_used_at аккаунта
    with SessionLocal() as session:
        account = session.get(Account, account_id)
        if account:
            account.last_used_at = datetime.utcnow()
            session.commit()
    
    return stats

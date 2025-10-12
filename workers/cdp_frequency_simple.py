"""
Простой CDP парсер - работает через UI но с CDP подключением
ПРОВЕРЕННЫЙ и РАБОЧИЙ вариант!
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Optional
from urllib.parse import quote

from playwright.async_api import async_playwright, Page

from ..core.db import SessionLocal
from ..core.models import Account, FrequencyResult


async def parse_frequency_cdp(
    account_id: int,
    masks: list[str],
    region: int = 225,
    cdp_url: str = "http://localhost:9222",
    on_progress: callable = None
) -> dict:
    """
    Парсинг через CDP подключение к запущенному Chrome
    
    Args:
        account_id: ID аккаунта  
        masks: Список масок
        region: Регион
        cdp_url: CDP URL (обычно http://localhost:9222)
        on_progress: Callback(mask, freq, current, total)
    
    Returns:
        {"success": int, "failed": int, "total": int}
    """
    
    # Записываем маски в БД как queued
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
    
    stats = {"success": 0, "failed": 0, "total": len(masks)}
    
    async with async_playwright() as p:
        try:
            # Подключаемся к уже запущенному Chrome
            browser = await p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            
            # Парсим каждую маску
            for idx, mask in enumerate(masks, 1):
                mask_norm = mask.strip()
                if not mask_norm:
                    continue
                
                try:
                    # Обновляем статус в БД
                    with SessionLocal() as session:
                        freq_result = session.query(FrequencyResult).filter(
                            FrequencyResult.mask == mask_norm,
                            FrequencyResult.region == region
                        ).first()
                        
                        if freq_result:
                            freq_result.status = 'running'
                            freq_result.attempts = (freq_result.attempts or 0) + 1
                            session.commit()
                    
                    # Парсим
                    freq = await _parse_single_mask(page, mask_norm, region)
                    
                    if freq:
                        # Сохраняем результат
                        with SessionLocal() as session:
                            freq_result = session.query(FrequencyResult).filter(
                                FrequencyResult.mask == mask_norm,
                                FrequencyResult.region == region
                            ).first()
                            
                            if freq_result:
                                freq_result.status = 'ok'
                                freq_result.freq_total = freq
                                freq_result.updated_at = datetime.utcnow()
                                freq_result.error = None
                                session.commit()
                        
                        stats["success"] += 1
                        
                        if on_progress:
                            on_progress(mask_norm, freq, idx, len(masks))
                    else:
                        # Ошибка парсинга
                        with SessionLocal() as session:
                            freq_result = session.query(FrequencyResult).filter(
                                FrequencyResult.mask == mask_norm,
                                FrequencyResult.region == region
                            ).first()
                            
                            if freq_result:
                                freq_result.status = 'error'
                                freq_result.error = 'Frequency not found'
                                freq_result.updated_at = datetime.utcnow()
                                session.commit()
                        
                        stats["failed"] += 1
                
                except Exception as e:
                    # Ошибка
                    with SessionLocal() as session:
                        freq_result = session.query(FrequencyResult).filter(
                            FrequencyResult.mask == mask_norm,
                            FrequencyResult.region == region
                        ).first()
                        
                        if freq_result:
                            freq_result.status = 'error'
                            freq_result.error = str(e)
                            freq_result.updated_at = datetime.utcnow()
                            session.commit()
                    
                    stats["failed"] += 1
                
                # Пауза между масками
                await asyncio.sleep(2)
            
            await browser.close()
        
        except Exception as e:
            print(f"[CDP Error] {e}")
            stats["failed"] = len(masks) - stats["success"]
    
    # Обновляем last_used_at аккаунта
    with SessionLocal() as session:
        account = session.get(Account, account_id)
        if account:
            account.last_used_at = datetime.utcnow()
            session.commit()
    
    return stats


async def _parse_single_mask(page: Page, mask: str, region: int) -> Optional[int]:
    """
    Парсит одну маску
    ПРАВИЛЬНАЯ логика парсинга!
    """
    # Открываем страницу с маской
    url = f"https://wordstat.yandex.ru/?words={quote(mask)}&regions={region}"
    await page.goto(url, wait_until="networkidle")
    await asyncio.sleep(2)
    
    # Проверяем капчу/логин
    content = await page.content()
    if "smartcaptcha" in content.lower():
        raise Exception("Captcha detected")
    
    if "passport" in page.url:
        raise Exception("Login required")
    
    # Парсим частоту из таблицы
    try:
        tables = await page.locator('table').all()
        
        if tables:
            table = tables[0]
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
        
        # Fallback: ищем в тексте страницы
        text = await page.inner_text("body")
        pattern = rf'{re.escape(mask)}[:\s]+(\d[\d\s]+\d{{3}})'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            freq_str = match.group(1).replace(' ', '').replace('\xa0', '').replace(',', '')
            return int(freq_str)
    
    except Exception as e:
        print(f"[Parse Error] {mask}: {e}")
    
    return None

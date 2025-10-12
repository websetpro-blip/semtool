"""
Воркер для парсинга частотности через сохранённые сессии
Пишет результаты прямо в БД (freq_results)
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Page

from ..core.db import SessionLocal
from ..core.models import Account, FrequencyResult
from ..services.sessions import _build_proxy_config


async def parse_frequency_with_session(
    account_id: int,
    masks: list[str],
    region: int = 225,
    headless: bool = True,
    on_progress: callable = None
) -> dict:
    """
    Парсит частотность используя сохранённую сессию аккаунта
    
    Args:
        account_id: ID аккаунта из БД
        masks: Список масок для парсинга
        region: Регион Яндекса
        headless: Фоновый режим
        on_progress: Callback для прогресса (mask, freq, idx, total)
    
    Returns:
        {'success': int, 'failed': int, 'errors': list}
    """
    # Загружаем аккаунт
    with SessionLocal() as session:
        account = session.get(Account, account_id)
        if not account:
            raise ValueError(f"Аккаунт #{account_id} не найден")
        
        profile_path = Path(account.profile_path)
        if not profile_path.exists():
            raise FileNotFoundError(f"Профиль не найден: {profile_path}")
        
        proxy = account.proxy
        account_name = account.name
    
    # Обеспечиваем записи в БД для всех масок
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
                    status='queued',
                    freq_total=0,
                    freq_exact=0
                ))
        session.commit()
    
    stats = {
        'success': 0,
        'failed': 0,
        'errors': []
    }
    
    # Парсинг через браузер
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(profile_path),
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-background-timer-throttling',
            ],
            viewport={"width": 1600, "height": 1200},
            proxy=_build_proxy_config(proxy) if proxy else None
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Открываем Wordstat
        await page.goto(f"https://wordstat.yandex.ru/?regions={region}", wait_until="networkidle")
        
        # Закрываем cookie уведомление
        try:
            cookie_btns = ["button:has-text('Accept')", "button:has-text('Принять')"]
            for btn in cookie_btns:
                try:
                    elem = page.locator(btn).first
                    if await elem.is_visible(timeout=1000):
                        await elem.click()
                        await asyncio.sleep(0.5)
                        break
                except:
                    pass
        except:
            pass
        
        # Парсим каждую маску
        total = len(masks)
        for idx, mask in enumerate(masks, 1):
            mask_norm = mask.strip()
            if not mask_norm:
                continue
            
            try:
                # Обновляем статус на "running"
                _update_status(mask_norm, region, 'running')
                
                # Парсим частоту
                freq = await _parse_single_mask(page, mask_norm, region)
                
                if freq is not None:
                    # Записываем в БД
                    _update_result(mask_norm, region, freq)
                    stats['success'] += 1
                    
                    if on_progress:
                        on_progress(mask_norm, freq, idx, total)
                else:
                    _update_status(mask_norm, region, 'error', error='Частота не найдена')
                    stats['failed'] += 1
                    stats['errors'].append(f"{mask_norm}: частота не найдена")
                
                # Пауза между запросами
                if idx < total:
                    delay = 2.0 + (idx % 3) * 0.5
                    await asyncio.sleep(delay)
                
            except Exception as e:
                error_msg = str(e)
                _update_status(mask_norm, region, 'error', error=error_msg)
                stats['failed'] += 1
                stats['errors'].append(f"{mask_norm}: {error_msg}")
        
        await context.close()
    
    # Обновляем last_used_at аккаунта
    with SessionLocal() as session:
        account = session.get(Account, account_id)
        if account:
            account.last_used_at = datetime.utcnow()
            session.commit()
    
    return stats


async def _parse_single_mask(page: Page, mask: str, region: int) -> Optional[int]:
    """Парсит частоту для одной маски"""
    
    # Открываем страницу с маской
    url = f"https://wordstat.yandex.ru/?words={mask.replace(' ', '+')}&regions={region}"
    await page.goto(url, wait_until="networkidle", timeout=30000)
    await asyncio.sleep(1.5)
    
    # Метод 1: Ищем "Общее число запросов ... : 190 467"
    try:
        page_text = await page.inner_text("body")
        
        # Вариант A: "Общее число запросов"
        match = re.search(r'Общее число запросов[^:]*:\s*([\d\s]+)', page_text)
        if match:
            freq_str = match.group(1).strip().replace(' ', '').replace(',', '')
            return int(freq_str)
        
        # Вариант B: Первое большое число в начале страницы
        first_text = page_text[:500]
        numbers = re.findall(r'\b(\d[\d\s]{3,})\b', first_text)
        if numbers:
            freq_str = numbers[0].replace(' ', '').replace(',', '')
            if len(freq_str) >= 3:
                return int(freq_str)
    
    except Exception:
        pass
    
    # Метод 2: Ищем в таблице
    try:
        selectors = [
            ".WordStat-Table .text-bold",
            ".wordstat-table__number",
            "[data-stat='main-table'] td:first-child"
        ]
        
        for selector in selectors:
            try:
                elem = page.locator(selector).first
                if await elem.is_visible(timeout=2000):
                    text = await elem.inner_text()
                    match = re.search(r'(\d[\d\s,]*)', text)
                    if match:
                        return int(match.group(1).replace(' ', '').replace(',', ''))
            except:
                continue
    
    except Exception:
        pass
    
    return None


def _update_status(mask: str, region: int, status: str, error: Optional[str] = None) -> None:
    """Обновляет статус записи в БД"""
    with SessionLocal() as session:
        result = session.query(FrequencyResult).filter(
            FrequencyResult.mask == mask,
            FrequencyResult.region == region
        ).first()
        
        if result:
            result.status = status
            result.updated_at = datetime.utcnow()
            result.attempts += 1
            
            if error:
                result.error = error
            
            session.commit()


def _update_result(mask: str, region: int, freq: int) -> None:
    """Записывает результат в БД"""
    with SessionLocal() as session:
        result = session.query(FrequencyResult).filter(
            FrequencyResult.mask == mask,
            FrequencyResult.region == region
        ).first()
        
        if result:
            result.status = 'ok'
            result.freq_total = freq
            result.freq_exact = 0  # Пока не парсим точную
            result.error = None
            result.updated_at = datetime.utcnow()
            session.commit()

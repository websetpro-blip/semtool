# services/direct_batch.py
from __future__ import annotations
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from .forecast_ui import forecast_batch
import asyncio

async def take_bids_for_phrases(
    phrases: List[str], 
    storage_state_path: str, 
    proxy: str|None = None, 
    region_ids: list[int] = None
) -> List[Dict[str, Any]]:
    """
    Получить ставки/показы/клики для списка фраз через Прогноз бюджета
    
    Args:
        phrases: список ключевых фраз
        storage_state_path: путь к сохраненной сессии
        proxy: прокси сервер (опционально)
        region_ids: список ID регионов
    
    Returns:
        Список словарей с метриками {phrase, shows, clicks, cost, cpc}
    """
    async with async_playwright() as p:
        # Запускаем браузер
        browser_args = ["--disable-dev-shm-usage", "--no-sandbox"]
        browser = await p.chromium.launch(
            headless=True, 
            args=browser_args
        )
        
        # Создаем контекст с авторизацией
        context_params = {
            "storage_state": storage_state_path,
            "viewport": {"width": 1280, "height": 800},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        }
        
        if proxy:
            context_params["proxy"] = {"server": proxy}
        
        context = await browser.new_context(**context_params)
        
        try:
            # Получаем прогноз
            data = await forecast_batch(context, phrases, region_ids or [225])
            return data
        finally:
            await context.close()
            await browser.close()

def get_bids_sync(phrases: List[str], storage_state: str, proxy: str = None) -> List[Dict[str, Any]]:
    """
    Синхронная обертка для получения ставок
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            take_bids_for_phrases(phrases, storage_state, proxy)
        )
    finally:
        loop.close()

def batch_forecast(phrases_chunks: List[List[str]], storage_state: str) -> Dict[str, Dict[str, Any]]:
    """
    Пакетная обработка больших списков фраз
    
    Args:
        phrases_chunks: список пачек фраз
        storage_state: путь к сессии
    
    Returns:
        Словарь {phrase: metrics}
    """
    result = {}
    
    for i, chunk in enumerate(phrases_chunks):
        print(f"Processing chunk {i+1}/{len(phrases_chunks)}...")
        
        try:
            data = get_bids_sync(chunk, storage_state)
            for item in data:
                if item["phrase"] != "__TOTAL__":
                    result[item["phrase"]] = item
        except Exception as e:
            print(f"Error in chunk {i+1}: {e}")
            continue
    
    return result

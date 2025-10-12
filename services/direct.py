"""
Yandex.Direct budget forecasting service for turbo parser.
Fetches CPC, impressions, and budget estimates for phrases.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from ..core.db import get_db_connection


async def forecast_batch_direct(
    phrases: list[dict],
    session_page=None,
    chunk_size: int = 100,
    region: int = 225
) -> list[dict]:
    """
    Forecast budget from Yandex.Direct for phrases.
    
    Args:
        phrases: List of dicts with 'phrase', 'freq', 'region'
        session_page: Playwright page with active session
        chunk_size: Number of phrases per batch (Direct limit: ~100/min)
        region: Yandex region ID
    
    Returns:
        List of dicts: [{'phrase': str, 'cpc': float, 'impressions': int, 'budget': float}, ...]
    """
    results = []
    
    from playwright.async_api import async_playwright
    
    # If no session, create temporary browser
    own_browser = session_page is None
    if own_browser:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        session_page = await context.new_page()
        await session_page.goto("https://direct.yandex.ru/")
    
    try:
        for i in range(0, len(phrases), chunk_size):
            batch = phrases[i:i + chunk_size]
            
            for phrase_data in batch:
                phrase = phrase_data['phrase']
                freq = phrase_data.get('freq', 0)
                
                try:
                    # Navigate to Direct forecast page
                    # Note: This URL structure is approximate - adjust based on actual Direct interface
                    url = f"https://direct.yandex.ru/registered/main.pl?cmd=advancedForecast&phrase={phrase}&region={region}"
                    await session_page.goto(url, timeout=15000)
                    
                    # Wait for forecast data
                    await session_page.wait_for_selector(
                        ".forecast-result, .forecast-table, .b-forecast",
                        timeout=10000
                    )
                    
                    # Extract CPC (cost per click)
                    try:
                        cpc_element = session_page.locator("[data-name='cpc'], .cpc-value, .b-forecast__cpc")
                        cpc_text = await cpc_element.first.inner_text(timeout=3000)
                        cpc = float(''.join(filter(lambda x: x.isdigit() or x == '.', cpc_text.replace(',', '.'))))
                    except:
                        # Fallback: estimate CPC from freq (rough heuristic)
                        cpc = estimate_cpc_from_freq(freq)
                    
                    # Extract impressions
                    try:
                        imp_element = session_page.locator("[data-name='impressions'], .impressions-value")
                        imp_text = await imp_element.first.inner_text(timeout=3000)
                        impressions = int(''.join(filter(str.isdigit, imp_text)))
                    except:
                        # Fallback: use freq as approximation
                        impressions = int(freq * 0.8) if freq > 0 else 0
                    
                    # Calculate budget (CPC * clicks, estimate CTR = 2%)
                    clicks = int(impressions * 0.02)  # 2% CTR
                    budget = round(cpc * clicks, 2)
                    
                    result = {
                        'phrase': phrase,
                        'cpc': cpc,
                        'impressions': impressions,
                        'budget': budget
                    }
                    results.append(result)
                    
                    # Save to DB
                    with get_db_connection() as conn:
                        conn.execute(
                            """INSERT OR REPLACE INTO forecasts 
                               (phrase, cpc, impressions, budget, freq_ref) 
                               VALUES (?, ?, ?, ?, ?)""",
                            (phrase, cpc, impressions, budget, phrase)
                        )
                    
                    # Rate limiting
                    await asyncio.sleep(0.8)
                    
                    print(f"[Direct] {phrase}: CPC {cpc}, Budget {budget}")
                    
                except Exception as e:
                    print(f"[Direct ERROR] {phrase}: {e}")
                    # Fallback to estimates
                    cpc = estimate_cpc_from_freq(freq)
                    impressions = int(freq * 0.8) if freq > 0 else 0
                    clicks = int(impressions * 0.02)
                    budget = round(cpc * clicks, 2)
                    
                    results.append({
                        'phrase': phrase,
                        'cpc': cpc,
                        'impressions': impressions,
                        'budget': budget
                    })
            
            # Pause between batches
            if i + chunk_size < len(phrases):
                await asyncio.sleep(2)
    
    finally:
        if own_browser:
            await context.close()
            await browser.close()
            await playwright.stop()
    
    return results


def estimate_cpc_from_freq(freq: int) -> float:
    """
    Estimate CPC based on frequency (rough heuristic).
    High freq = lower CPC (more competition)
    Low freq = higher CPC (niche)
    """
    if freq > 100000:
        return 15.0  # High competition
    elif freq > 10000:
        return 25.0
    elif freq > 1000:
        return 35.0
    elif freq > 100:
        return 50.0
    else:
        return 70.0  # Low freq, might be expensive


async def get_saved_forecasts(region: int = 225) -> list[dict]:
    """Get all saved forecast results from database."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """SELECT phrase, cpc, impressions, budget 
               FROM forecasts 
               ORDER BY budget DESC"""
        )
        return [
            {
                'phrase': row[0],
                'cpc': row[1],
                'impressions': row[2],
                'budget': row[3]
            }
            for row in cursor.fetchall()
        ]


async def merge_freq_and_forecast(freq_results: list[dict], forecast_results: list[dict]) -> list[dict]:
    """Merge frequency and forecast data by phrase."""
    # Create lookup dict for forecasts
    forecasts = {f['phrase']: f for f in forecast_results}
    
    merged = []
    for freq in freq_results:
        phrase = freq['phrase']
        forecast = forecasts.get(phrase, {})
        
        merged.append({
            **freq,  # phrase, freq, region
            **forecast  # cpc, impressions, budget
        })
    
    return merged

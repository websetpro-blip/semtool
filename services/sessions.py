"""
Управление браузерными сессиями для парсинга
Сессия = persistent_context браузера с сохранёнными куками
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext

from ..core.db import SessionLocal
from ..core.models import Account


SESSION_PROFILES_DIR = Path(".profiles")
SESSION_PROFILES_DIR.mkdir(exist_ok=True)


async def create_session_for_account(account_id: int, proxy: Optional[str] = None) -> str:
    """
    Создаёт/обновляет сессию для аккаунта
    Открывает браузер, пользователь логинится, сессия сохраняется
    
    Returns: путь к профилю сессии
    """
    with SessionLocal() as session:
        account = session.get(Account, account_id)
        if not account:
            raise ValueError(f"Аккаунт #{account_id} не найден")
        
        profile_path = SESSION_PROFILES_DIR / f"session_{account.name}"
        profile_path.mkdir(exist_ok=True)
        
        # Обновляем путь к профилю в БД
        account.profile_path = str(profile_path)
        session.commit()
    
    # Открываем браузер для ручного логина
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(profile_path),
            headless=False,
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled'
            ],
            viewport={"width": 1600, "height": 1200},
            proxy=_build_proxy_config(proxy) if proxy else None
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://wordstat.yandex.ru/", wait_until="networkidle")
        
        # Закрываем cookie уведомление если есть
        try:
            cookie_btns = [
                "button:has-text('Accept')",
                "button:has-text('Принять')",
                "[class*='cookie'] button"
            ]
            for btn in cookie_btns:
                try:
                    elem = page.locator(btn).first
                    if await elem.is_visible(timeout=1000):
                        await elem.click()
                        break
                except:
                    pass
        except:
            pass
        
        # Ждём 3 минуты на ручной логин
        print(f"[Сессия {account.name}] Залогинься в браузере...")
        print(f"[Сессия {account.name}] У тебя есть 3 минуты")
        await asyncio.sleep(180)
        
        # Проверяем что залогинился
        input_selectors = [
            "textarea[placeholder*='Введите']",
            "textarea",
            "input[type='text']"
        ]
        
        logged_in = False
        for selector in input_selectors:
            try:
                elem = page.locator(selector).first
                if await elem.is_visible(timeout=3000):
                    logged_in = True
                    break
            except:
                continue
        
        await context.close()
        
        if not logged_in:
            raise RuntimeError("Не удалось подтвердить авторизацию")
        
        # Обновляем статус аккаунта
        with SessionLocal() as db_session:
            account = db_session.get(Account, account_id)
            if account:
                account.status = 'ok'
                account.last_used_at = datetime.utcnow()
                db_session.commit()
        
        return str(profile_path)


async def check_session_status(profile_path: str) -> dict:
    """
    Проверяет живость сессии (есть ли авторизация)
    
    Returns: {'active': bool, 'message': str}
    """
    path = Path(profile_path)
    if not path.exists():
        return {'active': False, 'message': 'Профиль не найден'}
    
    try:
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                str(path),
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto("https://wordstat.yandex.ru/", wait_until="networkidle", timeout=30000)
            
            # Проверяем наличие поля ввода
            input_selectors = [
                "textarea[placeholder*='Введите']",
                "textarea",
                "input[type='text']"
            ]
            
            logged_in = False
            for selector in input_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.is_visible(timeout=3000):
                        logged_in = True
                        break
                except:
                    continue
            
            await context.close()
            
            if logged_in:
                return {'active': True, 'message': 'Сессия активна'}
            else:
                return {'active': False, 'message': 'Требуется авторизация'}
    
    except Exception as e:
        return {'active': False, 'message': f'Ошибка проверки: {e}'}


def _build_proxy_config(proxy_url: str) -> dict:
    """Парсит proxy URL в конфиг для Playwright"""
    from urllib.parse import urlparse, unquote
    
    parsed = urlparse(proxy_url)
    config = {
        "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
    }
    
    if parsed.username:
        config["username"] = unquote(parsed.username)
    if parsed.password:
        config["password"] = unquote(parsed.password)
    
    return config


def list_sessions() -> list[dict]:
    """Список всех аккаунтов с информацией о сессиях"""
    with SessionLocal() as session:
        accounts = session.query(Account).all()
        
        result = []
        for account in accounts:
            profile_path = Path(account.profile_path) if account.profile_path else None
            session_exists = profile_path and profile_path.exists()
            
            result.append({
                'account_id': account.id,
                'account_name': account.name,
                'profile_path': str(profile_path) if profile_path else None,
                'session_exists': session_exists,
                'status': account.status,
                'last_used': account.last_used_at,
                'proxy': account.proxy,
            })
        
        return result


def delete_session(account_id: int) -> None:
    """Удаляет сохранённую сессию аккаунта"""
    with SessionLocal() as session:
        account = session.get(Account, account_id)
        if not account or not account.profile_path:
            return
        
        profile_path = Path(account.profile_path)
        if profile_path.exists():
            import shutil
            shutil.rmtree(profile_path, ignore_errors=True)
        
        account.status = 'disabled'
        session.commit()

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import time

from sqlalchemy import select

from ..core.db import SessionLocal
from ..core.models import Account

# Для проверки прокси и автологина
try:
    import aiohttp
    import asyncio
    from playwright.async_api import async_playwright
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False


def _auto_refresh(session):
    now = datetime.utcnow()
    stmt = select(Account).where(Account.status.in_(['cooldown', 'captcha']))
    for acc in session.execute(stmt).scalars():
        if acc.cooldown_until and acc.cooldown_until <= now:
            acc.status = 'ok'
            acc.cooldown_until = None
            acc.captcha_tries = 0
    session.commit()


def list_accounts() -> list[Account]:
    with SessionLocal() as session:
        _auto_refresh(session)
        result = session.execute(select(Account).order_by(Account.name))
        return list(result.scalars())


def create_account(name: str, profile_path: str, proxy: str | None = None, notes: str | None = None) -> Account:
    with SessionLocal() as session:
        account = Account(name=name, profile_path=profile_path, proxy=proxy or None, notes=notes)
        session.add(account)
        session.commit()
        session.refresh(account)
        return account


def upsert_account(name: str, profile_path: str, proxy: str | None = None, notes: str | None = None) -> Account:
    with SessionLocal() as session:
        stmt = select(Account).where(Account.name == name)
        existing = session.execute(stmt).scalar_one_or_none()
        if existing:
            existing.profile_path = profile_path
            existing.proxy = proxy or None
            existing.notes = notes
            session.commit()
            session.refresh(existing)
            return existing
        account = Account(name=name, profile_path=profile_path, proxy=proxy or None, notes=notes)
        session.add(account)
        session.commit()
        session.refresh(account)
        return account


def update_account(account_id: int, **fields) -> Account:
    with SessionLocal() as session:
        account = session.get(Account, account_id)
        if account is None:
            raise ValueError(f'Account {account_id} not found')
        for key, value in fields.items():
            if hasattr(account, key):
                setattr(account, key, value)
        session.commit()
        session.refresh(account)
        return account


def delete_account(account_id: int) -> None:
    with SessionLocal() as session:
        account = session.get(Account, account_id)
        if account:
            session.delete(account)
            session.commit()


def set_status(account_id: int, status: str, *, cooldown_minutes: int | None = None, captcha_increment: bool = False) -> Account:
    with SessionLocal() as session:
        account = session.get(Account, account_id)
        if account is None:
            raise ValueError(f'Account {account_id} not found')
        account.status = status
        if cooldown_minutes is not None:
            account.cooldown_until = datetime.utcnow() + timedelta(minutes=cooldown_minutes)
        elif status == 'ok':
            account.cooldown_until = None
        if captcha_increment:
            account.captcha_tries = (account.captcha_tries or 0) + 1
        session.commit()
        session.refresh(account)
        return account


def mark_captcha(account_id: int, minutes: int = 30) -> Account:
    return set_status(account_id, 'captcha', cooldown_minutes=minutes, captcha_increment=True)


def mark_cooldown(account_id: int, minutes: int = 10) -> Account:
    return set_status(account_id, 'cooldown', cooldown_minutes=minutes)


def mark_error(account_id: int) -> Account:
    return set_status(account_id, 'error')


def mark_ok(account_id: int) -> Account:
    return set_status(account_id, 'ok')


def update_account_proxy(account_name: str, proxy: str | None) -> Account:
    """Обновить прокси у аккаунта по имени"""
    with SessionLocal() as session:
        stmt = select(Account).where(Account.name == account_name)
        account = session.execute(stmt).scalar_one_or_none()
        if account is None:
            raise ValueError(f'Account {account_name} not found')
        account.proxy = proxy
        session.commit()
        session.refresh(account)
        return account


# ========== НОВЫЕ ФУНКЦИИ ИЗ ФАЙЛА 42 ==========

async def test_proxy(proxy: Optional[str], timeout: int = 10) -> Dict[str, Any]:
    """
    Проверка прокси
    
    Returns:
        {"ok": True/False, "ip": "1.2.3.4" или "error": "описание ошибки"}
    """
    if not ASYNC_AVAILABLE:
        return {"ok": False, "error": "aiohttp не установлен"}
    
    if not proxy:
        return {"ok": True, "ip": None, "message": "Без прокси"}
    
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as session:
            async with session.get(
                "https://yandex.ru/internet",
                proxy=proxy,
                headers={"User-Agent": "Mozilla/5.0"}
            ) as resp:
                resp.raise_for_status()
                ip = resp.headers.get("x-client-ip") or "ok"
                return {"ok": True, "ip": ip}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_cookies_status(account: Account) -> str:
    """
    Статус куки аккаунта
    
    Returns:
        "None" | "Fresh" | "Expired"
    """
    # Куки хранятся в runtime/profiles/<name>.json (storage_state Playwright)
    profile_path = Path(account.profile_path)
    cookies_file = profile_path / "cookies.json"  # или storage_state.json
    
    # Проверяем несколько вариантов
    for possible_file in [
        cookies_file,
        profile_path / "storage_state.json",
        profile_path / "state.json"
    ]:
        if possible_file.exists():
            age_seconds = time.time() - possible_file.stat().st_mtime
            age_days = age_seconds / (24 * 3600)
            
            if age_days < 7:
                return "Fresh"
            else:
                return "Expired"
    
    return "None"


async def autologin_account(account: Account) -> Dict[str, Any]:
    """
    Автологин аккаунта через Playwright
    Открывает Wordstat, проверяет авторизацию, сохраняет storage_state
    
    Returns:
        {"ok": True/False, "message": "...", "storage_path": "..."}
    """
    if not ASYNC_AVAILABLE:
        return {"ok": False, "message": "Playwright не установлен"}
    
    profile_path = Path(account.profile_path)
    profile_path.mkdir(parents=True, exist_ok=True)
    storage_file = profile_path / "storage_state.json"
    
    try:
        from ..utils.proxy import parse_proxy
        proxy_config = parse_proxy(account.proxy) if account.proxy else None
        
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=False)
            
            context = await browser.new_context(
                proxy=proxy_config,
                viewport={"width": 1280, "height": 900}
            )
            
            page = await context.new_page()
            
            # Открываем Wordstat
            await page.goto("https://wordstat.yandex.ru/", timeout=60000)
            
            # Ждем загрузки
            await page.wait_for_load_state("domcontentloaded")
            
            # Проверяем авторизован ли
            current_url = page.url
            
            if "passport.yandex" in current_url or "passport.ya.ru" in current_url:
                await browser.close()
                return {
                    "ok": False,
                    "message": "Требуется ручной вход (открыта страница паспорта)"
                }
            
            # Сохраняем storage_state
            await context.storage_state(path=str(storage_file))
            await browser.close()
            
            # Обновляем last_used_at
            with SessionLocal() as session:
                stmt = select(Account).where(Account.id == account.id)
                acc = session.execute(stmt).scalar_one_or_none()
                if acc:
                    acc.last_used_at = datetime.utcnow()
                    session.commit()
            
            return {
                "ok": True,
                "message": "Авторизация успешна",
                "storage_path": str(storage_file)
            }
            
    except Exception as e:
        return {"ok": False, "message": f"Ошибка: {e}"}


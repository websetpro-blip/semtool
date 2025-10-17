from __future__ import annotations
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy import select, update, delete

from ..core.db import SessionLocal
from ..core.models import Account
from ..utils.text_fix import fix_mojibake

# Optional async deps
try:
    import aiohttp
    import asyncio
    from playwright.async_api import async_playwright
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

RUNTIME_DIR = Path("runtime")
RUNTIME_ACCOUNTS = RUNTIME_DIR / "runtimeaccounts.json"

COOKIE_STATUS_OK = "ok"
COOKIE_STATUS_EMPTY = "empty"
COOKIE_STATUS_EXPIRED = "expired"

PROXY_OK = "ok"
PROXY_BAD = "bad"


@dataclass
class AccountDTO:
    id: Optional[int] = None
    name: str = ""
    login: str = ""
    password: str = ""
    profile_path: str = ""
    proxy: Optional[str] = None
    secrets: Dict[str, Any] = field(default_factory=dict)
    cookies: Dict[str, Any] = field(default_factory=dict)
    cookie_status: str = COOKIE_STATUS_EMPTY
    status: str = COOKIE_STATUS_OK
    cooldown_until: Optional[datetime] = None
    captcha_tries: int = 0

    @staticmethod
    def from_model(acc: Account) -> "AccountDTO":
        return AccountDTO(
            id=acc.id,
            name=fix_mojibake(acc.name or ""),
            login=acc.login or "",
            password=acc.password or "",
            profile_path=fix_mojibake(acc.profile_path or ""),
            proxy=acc.proxy,
            secrets=acc.secrets or {},
            cookies=acc.cookies or {},
            cookie_status=acc.cookie_status or COOKIE_STATUS_EMPTY,
            status=acc.status or COOKIE_STATUS_OK,
            cooldown_until=acc.cooldown_until,
            captcha_tries=acc.captcha_tries or 0,
        )

    def to_model_update(self, acc: Account) -> Account:
        acc.name = fix_mojibake(self.name)
        acc.login = self.login
        acc.password = self.password
        acc.profile_path = fix_mojibake(self.profile_path)
        acc.proxy = self.proxy
        acc.secrets = self.secrets
        acc.cookies = self.cookies
        acc.cookie_status = self.cookie_status
        acc.status = self.status
        acc.cooldown_until = self.cooldown_until
        acc.captcha_tries = self.captcha_tries
        return acc


def _auto_refresh(session) -> None:
    now = datetime.utcnow()
    stmt = select(Account).where(Account.status.in_(["cooldown", "captcha"]))
    for acc in session.execute(stmt).scalars():
        if acc.cooldown_until and acc.cooldown_until <= now:
            acc.status = COOKIE_STATUS_OK
            acc.cooldown_until = None
            acc.captcha_tries = 0
    session.commit()


def _cookie_status_from_cookies(cookies: Dict[str, Any]) -> str:
    if not cookies:
        return COOKIE_STATUS_EMPTY
    # Heuristic: cookie dict provided with at least one non-empty value
    has_non_empty = any(bool(v) for v in cookies.values())
    return COOKIE_STATUS_OK if has_non_empty else COOKIE_STATUS_EMPTY


# CRUD operations

def list_accounts() -> List[AccountDTO]:
    with SessionLocal() as session:
        _auto_refresh(session)
        stmt = select(Account)
        return [AccountDTO.from_model(a) for a in session.execute(stmt).scalars()]


def get_account(acc_id: int) -> Optional[AccountDTO]:
    with SessionLocal() as session:
        _auto_refresh(session)
        acc = session.get(Account, acc_id)
        return AccountDTO.from_model(acc) if acc else None


def create_account(data: Dict[str, Any]) -> AccountDTO:
    with SessionLocal() as session:
        acc = Account(**data)
        acc.cookie_status = _cookie_status_from_cookies(data.get("cookies") or {})
        session.add(acc)
        session.commit()
        session.refresh(acc)
        return AccountDTO.from_model(acc)


def update_account(acc_id: int, data: Dict[str, Any]) -> Optional[AccountDTO]:
    with SessionLocal() as session:
        acc = session.get(Account, acc_id)
        if not acc:
            return None
        for k, v in data.items():
            setattr(acc, k, v)
        if "cookies" in data:
            acc.cookie_status = _cookie_status_from_cookies(acc.cookies)
        session.commit()
        session.refresh(acc)
        return AccountDTO.from_model(acc)


def delete_account(acc_id: int) -> bool:
    with SessionLocal() as session:
        acc = session.get(Account, acc_id)
        if not acc:
            return False
        session.delete(acc)
        session.commit()
        return True


# Runtime JSON integration

def load_runtime_accounts() -> List[Dict[str, Any]]:
    if not RUNTIME_ACCOUNTS.exists():
        return []
    try:
        return json.loads(RUNTIME_ACCOUNTS.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_runtime_accounts(accounts: List[Dict[str, Any]]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_ACCOUNTS.write_text(json.dumps(accounts, ensure_ascii=False, indent=2), encoding="utf-8")


def sync_accounts_to_runtime() -> None:
    # Export minimal safe subset
    accounts = []
    for dto in list_accounts():
        accounts.append({
            "id": dto.id,
            "name": dto.name,
            "login": dto.login,
            "profile_path": dto.profile_path,
            "proxy": dto.proxy,
            "cookie_status": dto.cookie_status,
            "status": dto.status,
        })
    save_runtime_accounts(accounts)


# Proxy utilities
async def _test_proxy_async(proxy: Optional[str], timeout: int = 10) -> Tuple[bool, Optional[str]]:
    if not proxy:
        return True, None  # no proxy required
    if not ASYNC_AVAILABLE:
        return False, "async deps missing"
    url = "https://api.ipify.org?format=json"
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=timeout)) as sess:
            async with sess.get(url, proxy=proxy) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return True, data.get("ip")
                return False, f"status {resp.status}"
    except Exception as e:
        return False, str(e)


def test_proxy(proxy: Optional[str], timeout: int = 10) -> Dict[str, Any]:
    if not ASYNC_AVAILABLE:
        return {"ok": False, "reason": "async deps missing"}
    ok, info = asyncio.get_event_loop().run_until_complete(_test_proxy_async(proxy, timeout))
    return {"ok": ok, "info": info}


# Autologin via Playwright
async def _autologin_async(login_url: str, login: str, password: str, proxy: Optional[str] = None,
                           cookie_path: Optional[Path] = None,
                           login_selector: str = "input[name='login']",
                           password_selector: str = "input[name='password']",
                           submit_selector: str = "button[type='submit']",
                           wait_selector: Optional[str] = None,
                           headless: bool = True) -> Dict[str, Any]:
    if not ASYNC_AVAILABLE:
        return {"ok": False, "reason": "async deps missing"}
    pw_proxy = None
    if proxy:
        # Support formats: http://user:pass@host:port, socks5://...
        pw_proxy = {"server": proxy}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, proxy=pw_proxy)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(login_url, timeout=45000)
        await page.fill(login_selector, login)
        await page.fill(password_selector, password)
        await page.click(submit_selector)
        if wait_selector:
            await page.wait_for_selector(wait_selector, timeout=45000)
        # collect cookies
        cookies = await context.cookies()
        await browser.close()
        return {"ok": True, "cookies": cookies}


def autologin_and_update(acc_id: int, login_url: str, selectors: Dict[str, str], headless: bool = True) -> Optional[AccountDTO]:
    if not ASYNC_AVAILABLE:
        return None
    with SessionLocal() as session:
        acc = session.get(Account, acc_id)
        if not acc:
            return None
        sel = {
            "login_selector": selectors.get("login_selector", "input[name='login']"),
            "password_selector": selectors.get("password_selector", "input[name='password']"),
            "submit_selector": selectors.get("submit_selector", "button[type='submit']"),
            "wait_selector": selectors.get("wait_selector"),
        }
        result = asyncio.get_event_loop().run_until_complete(
            _autologin_async(
                login_url=login_url,
                login=acc.login,
                password=acc.password,
                proxy=acc.proxy,
                cookie_path=None,
                headless=headless,
                **sel,
            )
        )
        if not result.get("ok"):
            acc.status = "login_failed"
            session.commit()
            return AccountDTO.from_model(acc)
        acc.cookies = result.get("cookies", {})
        acc.cookie_status = _cookie_status_from_cookies(acc.cookies)
        acc.status = COOKIE_STATUS_OK if acc.cookie_status == COOKIE_STATUS_OK else "need_login"
        session.commit()
        session.refresh(acc)
        return AccountDTO.from_model(acc)


# Maintenance helpers

def mark_captcha(acc_id: int, cooldown_minutes: int = 30) -> Optional[AccountDTO]:
    with SessionLocal() as session:
        acc = session.get(Account, acc_id)
        if not acc:
            return None
        acc.status = "captcha"
        acc.captcha_tries = (acc.captcha_tries or 0) + 1
        acc.cooldown_until = datetime.utcnow() + timedelta(minutes=cooldown_minutes)
        session.commit()
        session.refresh(acc)
        return AccountDTO.from_model(acc)


def mark_cooldown(acc_id: int, minutes: int) -> Optional[AccountDTO]:
    with SessionLocal() as session:
        acc = session.get(Account, acc_id)
        if not acc:
            return None
        acc.status = "cooldown"
        acc.cooldown_until = datetime.utcnow() + timedelta(minutes=minutes)
        session.commit()
        session.refresh(acc)
        return AccountDTO.from_model(acc)


def refresh_cookie_status(acc_id: int) -> Optional[AccountDTO]:
    with SessionLocal() as session:
        acc = session.get(Account, acc_id)
        if not acc:
            return None
        acc.cookie_status = _cookie_status_from_cookies(acc.cookies)
        if acc.cookie_status != COOKIE_STATUS_OK:
            acc.status = "need_login"
        session.commit()
        session.refresh(acc)
        return AccountDTO.from_model(acc)


def proxy_check_and_update(acc_id: int, timeout: int = 10) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        acc = session.get(Account, acc_id)
        if not acc:
            return None
        result = test_proxy(acc.proxy, timeout=timeout)
        acc.secrets = acc.secrets or {}
        acc.secrets["proxy_test"] = result
        acc.status = PROXY_OK if result.get("ok") else PROXY_BAD
        session.commit()
        return result

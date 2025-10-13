"""
Visual Browser Manager - CORRECTED
Uses 5 working profiles (NOT wordstat_main!)
According to semtool дорожная карта.md
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum
from playwright.async_api import async_playwright, Page, BrowserContext

class BrowserStatus(Enum):
    IDLE = "idle"
    STARTING = "starting"
    LOGGED_IN = "logged_in"
    LOGIN_REQUIRED = "login_required"
    PARSING = "parsing"
    ERROR = "error"

class BrowserInstance:
    """Single browser instance data"""
    def __init__(self, name):
        self.name = name
        # Каждый аккаунт использует СВОЙ профиль
        self.profile_path = f"C:\\AI\\yandex\\.profiles\\{name}"
        self.context = None
        self.page = None
        self.status = BrowserStatus.IDLE

class VisualBrowserManager:
    """Manager for multiple Chrome browsers with working profiles"""
    
    # CORRECT CONFIGURATION from semtool дорожная карта.md
    CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    # 5 WORKING PROFILES (NOT wordstat_main!)
    AUTHORIZED_PROFILES = [
        "dsmismirnov",
        "kuznepetya", 
        "vfefyodorov",
        "volkovsvolkow",
        "semenovmsemionov"
    ]
    
    def __init__(self, num_browsers: int = 3):
        self.num_browsers = min(num_browsers, len(self.AUTHORIZED_PROFILES))
        self.browsers = {}
        self.playwright = None
        
    async def start_browser(self, browser_id: int, account_name: str,
                           profile_path: str, proxy: Optional[str] = None):
        """Start Chrome with specified profile"""
        
        # Используем профиль конкретного аккаунта
        if not profile_path or profile_path == ".profiles/demo_account":
            # Если профиль не указан или demo - используем профиль аккаунта
            profile_path = f"C:/AI/yandex/.profiles/{account_name}"
        elif not profile_path.startswith("C:"):
            # Если путь относительный - делаем абсолютный
            profile_path = f"C:/AI/yandex/{profile_path}"
        
        print(f"[Browser {browser_id}] Starting Chrome for account: {account_name}")
        print(f"[Browser {browser_id}] Using profile: {profile_path}")
        
        browser_instance = BrowserInstance(account_name)
        browser_instance.profile_path = profile_path
        
        try:
            # Парсим прокси (из файла 41)
            from ..utils.proxy import parse_proxy
            proxy_config = parse_proxy(proxy) if proxy else None
            
            if proxy_config:
                print(f"[Browser {browser_id}] Proxy: {proxy_config['server']} (user: {proxy_config.get('username', 'none')})")
            
            # Используем launch_persistent_context с прокси (правильный способ из файла 41!)
            browser_instance.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                channel="chrome",  # Системный Chrome
                headless=False,
                proxy=proxy_config,  # ← ВАЖНО: прокси на уровне Playwright API!
                viewport={"width": 1280, "height": 900},
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--start-maximized',
                    '--no-first-run',
                    '--no-default-browser-check'
                ]
            )
            
            # Получаем или создаем страницу
            if browser_instance.context.pages:
                browser_instance.page = browser_instance.context.pages[0]
            else:
                browser_instance.page = await browser_instance.context.new_page()
            
            # Открываем Wordstat
            await browser_instance.page.goto("https://wordstat.yandex.ru/?region=225", wait_until="networkidle")
            browser_instance.status = BrowserStatus.LOGGED_IN
            print(f"[Browser {browser_id}] Chrome started with Playwright")
                
            self.browsers[browser_id] = browser_instance
            return browser_instance
            
        except Exception as e:
            print(f"[Browser] Error: {e}")
            browser_instance.status = BrowserStatus.ERROR
            return browser_instance
    
    async def start_all_browsers(self, accounts: List[Dict]) -> None:
        """Start browsers for multiple accounts ПАРАЛЛЕЛЬНО"""
        
        print(f"\n[VISUAL] Starting {self.num_browsers} browsers ПАРАЛЛЕЛЬНО...")
        
        # Start playwright (Playwright сам управляет процессами)
        self.playwright = await async_playwright().start()
        
        # Подготавливаем задачи для параллельного запуска
        tasks = []
        for i in range(self.num_browsers):
            if i < len(accounts):
                account = accounts[i]
                account_name = account.get('name', self.AUTHORIZED_PROFILES[i])
                profile_path = account.get('profile_path', f".profiles/{account_name}")
                proxy = account.get('proxy')
            else:
                # Use from authorized profiles if not enough accounts
                account_name = self.AUTHORIZED_PROFILES[i]
                profile_path = f".profiles/{account_name}"
                proxy = None
            
            # Добавляем задачу в список (НЕ ЖДЕМ!)
            task = self.start_browser(
                browser_id=i,
                account_name=account_name,
                profile_path=profile_path,
                proxy=proxy
            )
            tasks.append(task)
        
        # Запускаем ВСЕ браузеры ПАРАЛЛЕЛЬНО!
        await asyncio.gather(*tasks, return_exceptions=True)
        
        print("\n" + "="*60)
        print(f"  {self.num_browsers} BROWSERS STARTED")
        print("="*60)
        for i, (browser_id, browser) in enumerate(self.browsers.items()):
            print(f"  [{i}] {browser.name}: READY")
        print("="*60 + "\n")
    
    async def close_all(self):
        """Close all browsers"""
        for browser_id, browser_instance in self.browsers.items():
            try:
                if browser_instance.context:
                    await browser_instance.context.close()
                    print(f"[Browser {browser_id}] Closed")
            except:
                pass
        
        if self.playwright:
            await self.playwright.stop()
            print("[Playwright] Stopped")
        
        self.browsers = {}
    
    def calculate_window_position(self, browser_id: int) -> Dict[str, int]:
        """Window position (only one browser)"""
        return {'x': 0, 'y': 0, 'width': 1920, 'height': 1080}
    
    async def check_login_status(self, page: Page) -> bool:
        """Check if logged in"""
        try:
            await page.goto("https://wordstat.yandex.ru/", wait_until="networkidle")
            await page.wait_for_timeout(2000)
            return "passport" not in page.url
        except:
            return False

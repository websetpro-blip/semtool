"""
Visual Browser Manager - FIXED
Uses ONLY ONE Chrome with wordstat_main profile
According to ВАЖНО_КАКОЙ_БРАУЗЕР_ИСПОЛЬЗОВАТЬ.md
"""

import asyncio
import subprocess
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
    def __init__(self, name="wordstat_main"):
        self.name = name
        self.profile_path = r"C:\AI\yandex\.profiles\wordstat_main"
        self.context = None
        self.page = None
        self.status = BrowserStatus.IDLE

class VisualBrowserManager:
    """Manager for ONE Chrome with wordstat_main profile"""
    
    # CORRECT CONFIGURATION (from documentation)
    CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    PROFILE_PATH = r"C:\AI\yandex\.profiles\wordstat_main"
    AUTHORIZED_PROFILES = ["wordstat_main"]  # ONLY ONE!
    
    def __init__(self, num_browsers: int = 1):
        if num_browsers > 1:
            print("[WARNING] Requested {} browsers, but using ONLY 1 (wordstat_main)".format(num_browsers))
        self.num_browsers = 1  # ALWAYS 1
        self.browsers = {}
        self.playwright = None
        self.browser = None
        
    async def start_browser(self, browser_id: int, account_name: str,
                           profile_path: str, proxy: Optional[str] = None):
        """Start Chrome with wordstat_main profile"""
        
        # FORCE correct profile
        if account_name != "wordstat_main":
            print(f"[WARNING] Requested profile '{account_name}', using 'wordstat_main' instead")
            account_name = "wordstat_main"
            profile_path = self.PROFILE_PATH
        
        print(f"[Browser] Starting Chrome with wordstat_main profile...")
        print(f"[Browser] Profile: {self.PROFILE_PATH}")
        
        browser_instance = BrowserInstance("wordstat_main")
        browser_instance.profile_path = self.PROFILE_PATH
        
        try:
            # Launch Chrome through CDP
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], 
                         capture_output=True, shell=True)
            await asyncio.sleep(2)
            
            # Start Chrome with CDP
            chrome_process = subprocess.Popen([
                self.CHROME_PATH,
                f"--user-data-dir={self.PROFILE_PATH}",
                "--remote-debugging-port=9222",
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "https://wordstat.yandex.ru/"
            ])
            
            await asyncio.sleep(5)  # Wait for Chrome to start
            
            # Connect via CDP
            self.browser = await self.playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
            contexts = self.browser.contexts
            
            if contexts:
                browser_instance.context = contexts[0]
                pages = browser_instance.context.pages
                browser_instance.page = pages[0] if pages else await browser_instance.context.new_page()
                browser_instance.status = BrowserStatus.LOGGED_IN
                print("[Browser] Connected to Chrome via CDP")
            else:
                print("[Browser] No contexts found, creating new page...")
                browser_instance.context = await self.browser.new_context()
                browser_instance.page = await browser_instance.context.new_page()
                await browser_instance.page.goto("https://wordstat.yandex.ru/")
                
            self.browsers[0] = browser_instance
            return browser_instance
            
        except Exception as e:
            print(f"[Browser] Error: {e}")
            browser_instance.status = BrowserStatus.ERROR
            return browser_instance
    
    async def start_all_browsers(self, accounts: List[Dict]) -> None:
        """Start THE ONLY browser (wordstat_main)"""
        
        print("\n[VISUAL] Starting browser...")
        print("[VISUAL] Using ONLY wordstat_main profile")
        
        # Kill existing Chrome
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], 
                      capture_output=True, shell=True)
        await asyncio.sleep(2)
        
        # Start playwright
        self.playwright = await async_playwright().start()
        
        # Start THE ONLY browser
        await self.start_browser(
            browser_id=0,
            account_name="wordstat_main",
            profile_path=self.PROFILE_PATH,
            proxy=None  # No proxy for wordstat_main
        )
        
        print("\n" + "="*60)
        print("  BROWSER STARTED")
        print("="*60)
        print("  [0] wordstat_main: READY")
        print("="*60 + "\n")
    
    async def close_all(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("[Browser] Closed")
    
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

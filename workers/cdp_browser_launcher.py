"""
CDP Browser Launcher - запуск браузеров для парсинга
Открывает Chrome с CDP портами для подключения парсера
"""

import subprocess
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Optional

class CDPBrowserLauncher:
    """Запуск браузеров с CDP для парсинга"""
    
    # Путь к Chrome
    CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    
    # Рабочие профили из Browser Management (как на скриншоте)
    WORKING_ACCOUNTS = [
        {
            "name": "dsmismirnov",
            "profile": ".profiles/dsmismirnov",
            "port": 9222
        },
        {
            "name": "kuznepetya", 
            "profile": ".profiles/kuznepetya",
            "port": 9223
        },
        {
            "name": "semenovmsemionov",
            "profile": ".profiles/semenovmsemionov",
            "port": 9224
        },
        {
            "name": "vfefyodorov",
            "profile": ".profiles/vfefyodorov",
            "port": 9225
        },
        {
            "name": "volkovsvolkow",
            "profile": ".profiles/volkovsvolkow",
            "port": 9226
        }
    ]
    
    def __init__(self):
        self.processes = []
        self.base_path = Path("C:/AI/yandex")
        
    def kill_existing_chrome(self):
        """Закрыть существующие Chrome процессы"""
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", "chrome.exe"],
                capture_output=True, 
                shell=True
            )
            time.sleep(2)
        except:
            pass
    
    def launch_browser(self, account: Dict) -> Optional[subprocess.Popen]:
        """Запуск одного браузера с CDP"""
        name = account["name"]
        profile_path = self.base_path / account["profile"]
        port = account["port"]
        
        # Проверяем профиль
        if not profile_path.exists():
            print(f"[ERROR] Профиль не найден: {profile_path}")
            return None
        
        # Проверяем куки
        cookies_file = profile_path / "Default" / "Network" / "Cookies"
        if cookies_file.exists():
            cookie_size = cookies_file.stat().st_size / 1024
            print(f"[{name}] Cookies: {cookie_size:.1f}KB")
        else:
            print(f"[{name}] WARNING: Cookies not found!")
        
        # Запускаем Chrome с CDP
        cmd = [
            self.CHROME_PATH,
            f"--user-data-dir={profile_path}",
            f"--remote-debugging-port={port}",
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
            "https://wordstat.yandex.ru/?region=225"
        ]
        
        try:
            print(f"[{name}] Запуск Chrome на порту {port}...")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return process
        except Exception as e:
            print(f"[{name}] ERROR: {e}")
            return None
    
    def launch_all_browsers(self, accounts: Optional[List[Dict]] = None) -> bool:
        """Запустить все браузеры для парсинга"""
        
        # Используем переданные аккаунты или дефолтные
        if not accounts:
            accounts = self.WORKING_ACCOUNTS
        
        print("\n" + "="*70)
        print("   ЗАПУСК БРАУЗЕРОВ ДЛЯ ПАРСИНГА (CDP)")
        print("="*70)
        
        # Убиваем старые Chrome
        print("\n[*] Закрываю старые Chrome процессы...")
        self.kill_existing_chrome()
        
        # Запускаем новые
        successful = []
        for i, account in enumerate(accounts):
            print(f"\n[{i+1}/{len(accounts)}] {account['name']}")
            process = self.launch_browser(account)
            
            if process:
                self.processes.append(process)
                successful.append(account)
                print(f"  ✓ Запущен на порту {account['port']}")
                
                # Задержка между запусками
                if i < len(accounts) - 1:
                    time.sleep(3)
            else:
                print(f"  ✗ Не удалось запустить")
        
        print("\n" + "="*70)
        print(f"   РЕЗУЛЬТАТ: {len(successful)}/{len(accounts)} браузеров запущено")
        print("="*70)
        
        if successful:
            print("\nCDP порты для подключения парсера:")
            for acc in successful:
                print(f"  {acc['name']} → http://127.0.0.1:{acc['port']}")
            
            print("\n✅ Браузеры готовы для парсинга!")
            print("   Теперь можно запускать парсер.")
            return True
        else:
            print("\n❌ Не удалось запустить браузеры")
            return False
    
    def close_all_browsers(self):
        """Закрыть все запущенные браузеры"""
        for process in self.processes:
            try:
                process.terminate()
            except:
                pass
        self.processes = []
        print("Все браузеры закрыты")

# Для использования из GUI
def launch_browsers_for_parsing():
    """Функция для вызова из GUI"""
    launcher = CDPBrowserLauncher()
    return launcher.launch_all_browsers()

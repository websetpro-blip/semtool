"""
Модуль для проверки авторизации через реальный запрос к Wordstat
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
from typing import Dict, List, Optional


class AuthChecker:
    """Проверка авторизации аккаунтов через Wordstat"""
    
    async def check_account_auth(self, account_name: str, profile_path: str, 
                                 proxy: Optional[str] = None) -> Dict[str, any]:
        """
        Проверить авторизацию аккаунта через попытку поиска в Wordstat
        
        Returns:
            Dict с результатами:
            - is_authorized: bool - авторизован ли
            - needs_login: bool - требуется ли логин
            - status: str - статус проверки
        """
        result = {
            "is_authorized": False,
            "needs_login": True,
            "status": "checking"
        }
        
        playwright = None
        context = None
        
        try:
            playwright = await async_playwright().start()
            
            # Настройка прокси если есть
            proxy_config = None
            if proxy:
                proxy_str = str(proxy)
                # Убираем префикс http:// или https://
                proxy_str = proxy_str.replace("http://", "").replace("https://", "")
                
                # Формат: user:pass@ip:port
                if "@" in proxy_str:
                    auth, server = proxy_str.split("@")
                    if ":" in auth:
                        user, password = auth.split(":", 1)
                        proxy_config = {
                            "server": f"http://{server}",
                            "username": user,
                            "password": password
                        }
            
            # Запускаем браузер в фоновом режиме
            # Преобразуем путь в абсолютный для Windows
            abs_profile = str(Path(profile_path).absolute()).replace("\\", "/")
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=abs_profile,
                headless=True,  # Фоновый режим
                proxy=proxy_config,
                viewport={'width': 1280, 'height': 720},
                ignore_https_errors=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            
            page = await context.new_page()
            
            # Идем на Wordstat
            print(f"[AuthCheck] {account_name}: Opening Wordstat...")
            await page.goto("https://wordstat.yandex.ru", wait_until="networkidle", timeout=30000)
            
            # Ждем загрузки
            await asyncio.sleep(2)
            
            # Проверяем URL - если перенаправило на passport.yandex, значит не авторизован
            current_url = page.url
            if "passport.yandex" in current_url:
                print(f"[AuthCheck] {account_name}: Redirected to login - NOT AUTHORIZED")
                result["is_authorized"] = False
                result["needs_login"] = True
                result["status"] = "need_login"
            else:
                # Пробуем ввести поисковый запрос
                try:
                    # Ищем поле ввода
                    search_input = await page.query_selector('input[name="words"]')
                    if not search_input:
                        search_input = await page.query_selector('textarea[name="words"]')
                    
                    if search_input:
                        # Вводим тестовое слово
                        await search_input.type("test", delay=100)
                        
                        # Ищем кнопку поиска
                        search_button = await page.query_selector('button[type="submit"]')
                        if not search_button:
                            search_button = await page.query_selector('input[type="submit"]')
                        
                        if search_button:
                            # Кликаем поиск
                            await search_button.click()
                            await asyncio.sleep(3)
                            
                            # Проверяем результат
                            current_url = page.url
                            if "passport.yandex" in current_url:
                                # Перенаправило на логин
                                print(f"[AuthCheck] {account_name}: Login required after search - NOT AUTHORIZED")
                                result["is_authorized"] = False
                                result["needs_login"] = True
                                result["status"] = "need_login"
                            elif "captcha" in current_url.lower():
                                # Капча
                                print(f"[AuthCheck] {account_name}: Captcha detected - PARTIALLY AUTHORIZED")
                                result["is_authorized"] = True
                                result["needs_login"] = False
                                result["status"] = "captcha"
                            else:
                                # Успешно выполнен поиск
                                print(f"[AuthCheck] {account_name}: Search successful - AUTHORIZED")
                                result["is_authorized"] = True
                                result["needs_login"] = False
                                result["status"] = "authorized"
                        else:
                            # Не нашли кнопку поиска, но мы на Wordstat
                            print(f"[AuthCheck] {account_name}: On Wordstat page - AUTHORIZED")
                            result["is_authorized"] = True
                            result["needs_login"] = False
                            result["status"] = "authorized"
                    else:
                        # Не нашли поле ввода - проверяем что на странице
                        if "wordstat" in current_url:
                            print(f"[AuthCheck] {account_name}: On Wordstat but no search field - CHECK MANUALLY")
                            result["is_authorized"] = True
                            result["needs_login"] = False
                            result["status"] = "check_manually"
                        else:
                            print(f"[AuthCheck] {account_name}: Unknown page - NOT AUTHORIZED")
                            result["is_authorized"] = False
                            result["needs_login"] = True
                            result["status"] = "unknown"
                            
                except Exception as e:
                    print(f"[AuthCheck] {account_name}: Error during search test: {e}")
                    # Если ошибка при поиске, но мы на Wordstat - считаем авторизованным
                    if "wordstat" in page.url:
                        result["is_authorized"] = True
                        result["needs_login"] = False
                        result["status"] = "authorized_with_errors"
                    else:
                        result["is_authorized"] = False
                        result["needs_login"] = True
                        result["status"] = "error"
            
        except Exception as e:
            print(f"[AuthCheck] {account_name}: Error: {e}")
            result["is_authorized"] = False
            result["needs_login"] = True
            result["status"] = f"error: {str(e)}"
            
        finally:
            # Закрываем браузер
            if context:
                await context.close()
            if playwright:
                await playwright.stop()
        
        return result
    
    async def check_multiple_accounts(self, accounts: List[Dict]) -> Dict[str, Dict]:
        """
        Проверить несколько аккаунтов параллельно
        
        Args:
            accounts: список словарей с данными аккаунтов
                     [{"name": "...", "profile_path": "...", "proxy": "..."}, ...]
        
        Returns:
            Dict с результатами для каждого аккаунта
        """
        tasks = []
        for acc in accounts:
            task = self.check_account_auth(
                acc["name"],
                acc.get("profile_path", f".profiles/{acc['name']}"),
                acc.get("proxy")
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Создаем словарь результатов
        result_dict = {}
        for acc, result in zip(accounts, results):
            result_dict[acc["name"]] = result
        
        return result_dict


# Функция для быстрой проверки одного аккаунта
async def quick_check(account_name: str, profile_path: Optional[str] = None, 
                     proxy: Optional[str] = None) -> bool:
    """
    Быстрая проверка авторизации одного аккаунта
    
    Returns:
        True если авторизован, False если нет
    """
    if not profile_path:
        profile_path = f".profiles/{account_name}"
    
    checker = AuthChecker()
    result = await checker.check_account_auth(account_name, profile_path, proxy)
    return result["is_authorized"]

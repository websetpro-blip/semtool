"""
Модуль для реальной проверки авторизации через Wordstat
Открывает браузер, переходит на Wordstat, вводит тестовое слово и проверяет редирект
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Tuple
from playwright.async_api import async_playwright, Page, BrowserContext

class WordstatAuthChecker:
    """Проверка авторизации через реальное открытие Wordstat"""
    
    def __init__(self, account_name: str, profile_path: Optional[str] = None):
        self.account_name = account_name
        self.profile_path = profile_path or f".profiles/{account_name}"
        self.context = None
        self.page = None
        
    async def check_authorization(self) -> Tuple[bool, str]:
        """
        Проверяет авторизацию через реальный поиск в Wordstat
        Returns: (is_authorized, status_message)
        """
        try:
            async with async_playwright() as p:
                # Запускаем браузер с профилем
                self.context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(Path(self.profile_path).absolute()),
                    channel="chrome",
                    headless=True,  # Не показываем окно при проверке
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )
                
                self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
                
                # Переходим на Wordstat
                await self.page.goto("https://wordstat.yandex.ru", wait_until="networkidle", timeout=10000)
                
                # Ждем загрузки страницы
                await self.page.wait_for_timeout(1000)
                
                # Проверяем URL - если редирект на passport, то не авторизован
                current_url = self.page.url
                if "passport.yandex" in current_url:
                    await self.context.close()
                    return False, "Redirect to login page"
                
                # Пробуем ввести тестовое слово
                try:
                    # Ищем поле ввода
                    search_input = await self.page.wait_for_selector(
                        'input[name="text"], input[type="text"]', 
                        timeout=3000
                    )
                    
                    # Вводим тестовое слово
                    await search_input.fill("тест")
                    
                    # Нажимаем Enter или кнопку поиска
                    await search_input.press("Enter")
                    
                    # Ждем результата
                    await self.page.wait_for_timeout(2000)
                    
                    # Проверяем снова URL после поиска
                    current_url = self.page.url
                    if "passport.yandex" in current_url:
                        await self.context.close()
                        return False, "Redirected to login after search"
                    
                    # Проверяем наличие результатов или капчи
                    if await self.page.query_selector(".captcha__image"):
                        await self.context.close()
                        return True, "Authorized but captcha required"
                    
                    if await self.page.query_selector(".b-word-statistics__table"):
                        await self.context.close()
                        return True, "Authorized and working"
                    
                    # Если есть сообщение об ошибке
                    if await self.page.query_selector(".error-message"):
                        await self.context.close()
                        return False, "Error on search"
                        
                    await self.context.close()
                    return True, "Authorized"
                    
                except Exception as e:
                    await self.context.close()
                    return False, f"Cannot perform search: {str(e)}"
                    
        except Exception as e:
            if self.context:
                await self.context.close()
            return False, f"Check failed: {str(e)}"
            
    async def login_and_save(self, login: str, password: str) -> Tuple[bool, str]:
        """
        Автоматический логин и сохранение куков
        """
        try:
            async with async_playwright() as p:
                # Запускаем браузер с профилем (показываем окно для логина)
                self.context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(Path(self.profile_path).absolute()),
                    channel="chrome",
                    headless=False,  # Показываем окно при логине
                    args=['--start-maximized']
                )
                
                self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
                
                # Переходим на Wordstat
                await self.page.goto("https://wordstat.yandex.ru")
                await self.page.wait_for_timeout(2000)
                
                # Проверяем редирект на логин
                if "passport.yandex" not in self.page.url:
                    # Уже авторизован
                    await self.context.close()
                    return True, "Already authorized"
                
                # Вводим логин
                try:
                    login_input = await self.page.wait_for_selector('input[name="login"]', timeout=5000)
                    await login_input.fill(login)
                    
                    # Нажимаем далее
                    submit_btn = await self.page.query_selector('button[type="submit"]')
                    if submit_btn:
                        await submit_btn.click()
                    else:
                        await login_input.press("Enter")
                        
                    await self.page.wait_for_timeout(2000)
                    
                    # Вводим пароль
                    password_input = await self.page.wait_for_selector('input[name="passwd"]', timeout=5000)
                    await password_input.fill(password)
                    
                    # Отправляем форму
                    submit_btn = await self.page.query_selector('button[type="submit"]')
                    if submit_btn:
                        await submit_btn.click()
                    else:
                        await password_input.press("Enter")
                    
                    # Ждем авторизации
                    await self.page.wait_for_timeout(3000)
                    
                    # Проверяем успешность
                    if "wordstat.yandex.ru" in self.page.url and "passport" not in self.page.url:
                        await self.context.close()
                        return True, "Login successful"
                    
                    # Если есть секретный вопрос - нужен ручной ввод
                    if await self.page.query_selector('input[name="question"]'):
                        # Оставляем браузер открытым для ручного ввода
                        return False, "Secret question required - please enter manually"
                    
                    await self.context.close()
                    return False, "Login failed"
                    
                except Exception as e:
                    await self.context.close()
                    return False, f"Login error: {str(e)}"
                    
        except Exception as e:
            if self.context:
                await self.context.close()
            return False, f"Failed to open browser: {str(e)}"


async def check_account_auth(account_name: str, profile_path: Optional[str] = None) -> Dict:
    """Быстрая проверка авторизации аккаунта"""
    checker = WordstatAuthChecker(account_name, profile_path)
    is_authorized, status = await checker.check_authorization()
    return {
        "account": account_name,
        "authorized": is_authorized,
        "status": status
    }


async def login_account(account_name: str, login: str, password: str, profile_path: Optional[str] = None) -> Dict:
    """Автоматический логин аккаунта"""
    checker = WordstatAuthChecker(account_name, profile_path)
    success, message = await checker.login_and_save(login, password)
    return {
        "account": account_name,
        "success": success,
        "message": message
    }


if __name__ == "__main__":
    # Тестирование
    async def test():
        # Проверяем авторизацию dsmismirnov
        result = await check_account_auth("dsmismirnov")
        print(f"Check result: {result}")
        
    asyncio.run(test())

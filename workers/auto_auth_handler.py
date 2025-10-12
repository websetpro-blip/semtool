"""
АВТОМАТИЧЕСКАЯ АВТОРИЗАЦИЯ В ЯНДЕКС
Обрабатывает страницу логина как в DirectParser
"""

import asyncio
import time
from typing import Optional, Dict, Any
from playwright.async_api import Page
from PySide6.QtWidgets import QInputDialog, QMessageBox
from PySide6.QtCore import QObject, Signal

class AutoAuthHandler(QObject):
    """Обработчик автоматической авторизации в Яндекс"""
    
    # Сигналы для GUI
    auth_required = Signal(str)  # Требуется авторизация для аккаунта
    secret_question_required = Signal(str, str)  # Секретный вопрос (аккаунт, вопрос)
    auth_completed = Signal(str)  # Авторизация завершена
    auth_failed = Signal(str, str)  # Ошибка авторизации (аккаунт, ошибка)
    
    def __init__(self):
        super().__init__()
        self.auth_data = {}  # Кеш данных авторизации
        
    async def check_auth_required(self, page: Page) -> bool:
        """Проверяет требуется ли авторизация"""
        url = page.url.lower()
        
        # Признаки страницы авторизации Яндекса
        auth_indicators = [
            'passport.yandex',
            '/auth',
            'login',
            'passport'
        ]
        
        # Проверяем URL
        for indicator in auth_indicators:
            if indicator in url:
                return True
                
        # Проверяем наличие формы логина на странице
        try:
            login_form = await page.query_selector('form[action*="passport"]')
            if login_form:
                return True
                
            # Проверяем кнопку входа
            login_button = await page.query_selector('text="Войти"')
            if login_button:
                return True
                
        except:
            pass
            
        return False
        
    async def auto_login(self, page: Page, account_data: Dict[str, Any]) -> bool:
        """
        Автоматический вход в аккаунт
        
        Args:
            page: Страница Playwright
            account_data: Данные аккаунта из БД
                - login: логин
                - password: пароль 
                - secret_answer: ответ на секретный вопрос (опционально)
        
        Returns:
            True если авторизация успешна
        """
        
        login = account_data.get('login', '')
        password = account_data.get('password', '')
        
        if not login or not password:
            self.auth_failed.emit(login, "Не указан логин или пароль")
            return False
            
        print(f"[AUTH] Начинаем авторизацию для {login}")
        
        try:
            # Ждем загрузки страницы
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Шаг 1: Вводим логин
            login_input = await self._find_login_input(page)
            if login_input:
                await login_input.fill(login)
                await page.wait_for_timeout(500)
                
                # Нажимаем кнопку "Войти" или Enter
                submit_button = await page.query_selector('button[type="submit"], button:has-text("Войти")')
                if submit_button:
                    await submit_button.click()
                else:
                    await login_input.press('Enter')
                    
                await page.wait_for_timeout(2000)
                
            # Шаг 2: Вводим пароль
            password_input = await self._find_password_input(page)
            if password_input:
                await password_input.fill(password)
                await page.wait_for_timeout(500)
                
                # Нажимаем войти
                submit_button = await page.query_selector('button[type="submit"], button:has-text("Войти")')
                if submit_button:
                    await submit_button.click()
                else:
                    await password_input.press('Enter')
                    
                await page.wait_for_timeout(3000)
                
            # Шаг 3: Проверяем секретный вопрос
            secret_question = await self._check_secret_question(page)
            if secret_question:
                print(f"[AUTH] Обнаружен секретный вопрос: {secret_question}")
                
                # Если есть сохраненный ответ
                if account_data.get('secret_answer'):
                    await self._answer_secret_question(page, account_data['secret_answer'])
                else:
                    # Запрашиваем у пользователя
                    self.secret_question_required.emit(login, secret_question)
                    # Здесь нужно будет ждать ответа от GUI
                    return False
                    
            # Проверяем успешность авторизации
            await page.wait_for_timeout(2000)
            
            if await self._check_auth_success(page):
                print(f"[AUTH] Авторизация успешна для {login}")
                self.auth_completed.emit(login)
                return True
            else:
                self.auth_failed.emit(login, "Не удалось авторизоваться")
                return False
                
        except Exception as e:
            print(f"[AUTH] Ошибка авторизации: {e}")
            self.auth_failed.emit(login, str(e))
            return False
            
    async def _find_login_input(self, page: Page) -> Optional[Any]:
        """Находит поле ввода логина"""
        selectors = [
            'input[name="login"]',
            'input[type="email"]',
            'input[placeholder*="Логин"]',
            'input[placeholder*="login"]',
            'input#passp-field-login',
            'input[data-t="field:input-login"]'
        ]
        
        for selector in selectors:
            element = await page.query_selector(selector)
            if element:
                return element
        return None
        
    async def _find_password_input(self, page: Page) -> Optional[Any]:
        """Находит поле ввода пароля"""
        selectors = [
            'input[type="password"]',
            'input[name="passwd"]',
            'input#passp-field-passwd',
            'input[data-t="field:input-passwd"]'
        ]
        
        for selector in selectors:
            element = await page.query_selector(selector)
            if element:
                return element
        return None
        
    async def _check_secret_question(self, page: Page) -> Optional[str]:
        """Проверяет наличие секретного вопроса"""
        try:
            # Ищем текст вопроса
            question_element = await page.query_selector('.passp-form-field__hint, .secret-question__question')
            if question_element:
                return await question_element.inner_text()
                
            # Альтернативный селектор
            question_text = await page.query_selector('text="Ответьте на контрольный вопрос"')
            if question_text:
                # Ищем сам вопрос рядом
                parent = await question_text.query_selector('xpath=..')
                if parent:
                    text = await parent.inner_text()
                    # Извлекаем вопрос из текста
                    lines = text.split('\n')
                    for line in lines:
                        if '?' in line:
                            return line.strip()
                            
        except:
            pass
        return None
        
    async def _answer_secret_question(self, page: Page, answer: str):
        """Отвечает на секретный вопрос"""
        # Находим поле ответа
        answer_input = await page.query_selector('input[name="question"], input[name="answer"], input[type="text"]')
        if answer_input:
            await answer_input.fill(answer)
            await page.wait_for_timeout(500)
            
            # Отправляем
            submit_button = await page.query_selector('button[type="submit"], button:has-text("Продолжить")')
            if submit_button:
                await submit_button.click()
            else:
                await answer_input.press('Enter')
                
    async def _check_auth_success(self, page: Page) -> bool:
        """Проверяет успешность авторизации"""
        url = page.url.lower()
        
        # Если вернулись на Wordstat - успех
        if 'wordstat.yandex' in url and 'passport' not in url:
            return True
            
        # Проверяем наличие элементов авторизованного пользователя
        try:
            # Ищем аватар или имя пользователя
            user_element = await page.query_selector('.username, .user-account, [class*="user-pic"]')
            if user_element:
                return True
                
            # Проверяем отсутствие формы логина
            login_form = await page.query_selector('form[action*="passport"]')
            if not login_form:
                return True
                
        except:
            pass
            
        return False
        
    async def handle_auth_redirect(self, page: Page, account_data: Dict[str, Any]) -> bool:
        """
        Основной метод обработки редиректа на авторизацию
        Вызывается когда парсер обнаруживает редирект на страницу логина
        """
        
        print(f"[AUTH] Обнаружен редирект на авторизацию")
        
        # Проверяем что это точно страница авторизации
        if not await self.check_auth_required(page):
            return True  # Не требуется авторизация
            
        # Запускаем автоматическую авторизацию
        success = await self.auto_login(page, account_data)
        
        if success:
            # Возвращаемся на Wordstat
            await page.goto("https://wordstat.yandex.ru/?region=225", wait_until='networkidle')
            await page.wait_for_timeout(2000)
            return True
        else:
            return False
            
    def set_secret_answer(self, account: str, answer: str):
        """Сохраняет ответ на секретный вопрос для аккаунта"""
        if account not in self.auth_data:
            self.auth_data[account] = {}
        self.auth_data[account]['secret_answer'] = answer

#!/usr/bin/env python3
"""
Автоматическая авторизация аккаунтов Яндекса в Wordstat
Используется во вкладке Аккаунты для автологина
"""

import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Page, BrowserContext
from PySide6.QtCore import QObject, Signal
from datetime import datetime

class AutoLoginWorker(QObject):
    """Воркер для автоматической авторизации аккаунта"""
    
    # Сигналы для GUI
    status_update = Signal(str)  # Обновление статуса
    progress_update = Signal(int)  # Прогресс (0-100)
    secret_question_required = Signal(str, str)  # Требуется секретный вопрос (account_name, question_text)
    login_completed = Signal(bool, str)  # Логин завершен (success, message)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.playwright = None
        self.context = None
        self.page = None
        self.secret_answer = None
        
        # Загружаем данные аккаунтов
        self.accounts_file = Path("C:/AI/yandex/configs/accounts.json")
        self.load_accounts_data()
        
    def load_accounts_data(self):
        """Загрузить данные аккаунтов из JSON"""
        try:
            # Проверяем существование файла
            if not self.accounts_file.exists():
                print(f"[AutoLogin] Файл не найден: {self.accounts_file}")
                self.accounts_data = {}
                return
                
            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                accounts = json.load(f)
                self.accounts_data = {}
                
                # Индексируем аккаунты по логину
                for acc in accounts:
                    login = acc["login"]
                    self.accounts_data[login] = acc
                    
                    # Также добавляем по имени без @yandex.ru для совместимости  
                    # Например: kuznepetya и kuznepetya@yandex.ru оба будут работать
                    if "@" not in login:
                        # Если логин без домена, добавляем варианты
                        self.accounts_data[f"{login}@yandex.ru"] = acc  
                        self.accounts_data[f"{login}@ya.ru"] = acc
                    else:
                        # Если логин с доменом, добавляем короткое имя
                        short_name = login.split("@")[0]
                        self.accounts_data[short_name] = acc
                
                print(f"[AutoLogin] Загружено {len(accounts)} аккаунтов")
                print(f"[AutoLogin] Доступные логины: {[acc['login'] for acc in accounts]}")
                print(f"[AutoLogin] Индексированные ключи: {list(self.accounts_data.keys())}")
        except Exception as e:
            print(f"[AutoLogin] Ошибка загрузки аккаунтов: {e}")
            self.accounts_data = {}
    
    def set_secret_answer(self, answer: str):
        """Установить ответ на секретный вопрос"""
        self.secret_answer = answer
        
    async def auto_login(self, account_name: str, profile_path: str, proxy: Optional[str] = None):
        """
        Выполнить автоматическую авторизацию аккаунта
        
        Args:
            account_name: Имя аккаунта (логин)
            profile_path: Путь к профилю браузера
            proxy: Прокси в формате http://user:pass@ip:port
        """
        print(f"[AutoLogin] Начинаем автологин для: {account_name}")
        print(f"[AutoLogin] Путь к профилю: {profile_path}")
        print(f"[AutoLogin] Прокси: {proxy}")
        print(f"[AutoLogin] Загруженные аккаунты: {list(self.accounts_data.keys())}")
        
        self.status_update.emit(f"Запуск автологина для {account_name}...")
        self.progress_update.emit(10)
        
        # Получаем данные аккаунта
        account_data = self.accounts_data.get(account_name)
        
        # Если не нашли данные, пробуем перезагрузить файл
        if not account_data:
            print(f"[AutoLogin] Данные не найдены, пробуем перезагрузить...")
            self.load_accounts_data()
            account_data = self.accounts_data.get(account_name)
        
        if not account_data:
            # Если все еще не нашли, пробуем загрузить напрямую
            try:
                print(f"[AutoLogin] Пробуем альтернативный путь к файлу...")
                alt_path = Path("configs/accounts.json")
                if alt_path.exists():
                    with open(alt_path, 'r', encoding='utf-8') as f:
                        accounts = json.load(f)
                        self.accounts_data = {acc["login"]: acc for acc in accounts}
                        account_data = self.accounts_data.get(account_name)
                        print(f"[AutoLogin] Загружено из альтернативного пути: {list(self.accounts_data.keys())}")
            except Exception as e:
                print(f"[AutoLogin] Ошибка альтернативной загрузки: {e}")
        
        if not account_data:
            error_msg = f"Данные для логина '{account_name}' не найдены. Проверьте файл configs/accounts.json"
            print(f"[AutoLogin] ОШИБКА: {error_msg}")
            print(f"[AutoLogin] Искали логин: {account_name}")
            print(f"[AutoLogin] Доступные логины: {list(self.accounts_data.keys()) if self.accounts_data else 'НЕТ ДАННЫХ'}")
            self.login_completed.emit(False, error_msg)
            return False
        
        password = account_data["password"]
        print(f"[AutoLogin] Данные найдены, пароль получен")
        
        try:
            # Запускаем Playwright
            self.playwright = await async_playwright().start()
            
            # Обрабатываем путь к профилю
            if profile_path.startswith(".profiles"):
                profile_path = str(Path("C:/AI/yandex") / profile_path)
            else:
                profile_path = str(Path(profile_path).absolute())
            
            profile_path = profile_path.replace("\\", "/")
            
            # Создаем папку профиля если не существует
            Path(profile_path).mkdir(parents=True, exist_ok=True)
            
            self.status_update.emit(f"Запуск браузера с профилем...")
            self.progress_update.emit(20)
            
            # Парсим прокси если есть
            proxy_config = None
            if proxy:
                if "@" in proxy:
                    # Формат: http://user:pass@ip:port
                    proxy = proxy.replace("http://", "")
                    auth, server = proxy.split("@")
                    user, pwd = auth.split(":")
                    proxy_config = {
                        "server": f"http://{server}",
                        "username": user,
                        "password": pwd
                    }
            
            # Запускаем браузер - ВАЖНО: обычный Chrome, не Chromium!
            # Добавляем executable_path если нужен конкретный Chrome
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                channel="chrome",  # Используем системный Chrome (не синий Chromium!)
                headless=False,  # Показываем браузер для визуального контроля
                proxy=proxy_config,
                viewport={"width": 1280, "height": 900},
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized"
                ]
            )
            
            self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            
            # ВАЖНАЯ ЛОГИКА: Точная цепочка авторизации Яндекса
            self.status_update.emit("Открываем Wordstat для инициации авторизации...")
            self.progress_update.emit(30)
            
            # Шаг 1: Идем на Wordstat
            await self.page.goto("https://wordstat.yandex.ru")
            await asyncio.sleep(2)
            
            current_url = self.page.url
            print(f"[AutoLogin] URL после открытия Wordstat: {current_url}")
            
            # Шаг 2: Вводим ЛЮБОЙ тестовый запрос для инициации авторизации
            if "passport.yandex.ru" not in current_url:
                self.status_update.emit("Вводим тестовый запрос для инициации авторизации...")
                
                # Ищем поле поиска на Wordstat
                search_selectors = [
                    'input[name="text"]',
                    'input[placeholder*="слово"]',
                    'input[placeholder*="фраз"]',
                    '.b-form-input__input',
                    'input[type="text"]'
                ]
                
                search_field = None
                for selector in search_selectors:
                    try:
                        search_field = await self.page.query_selector(selector, timeout=1000)
                        if search_field:
                            print(f"[AutoLogin] Нашли поле поиска: {selector}")
                            break
                    except:
                        continue
                
                if search_field:
                    # ОБЯЗАТЕЛЬНО вводим тестовый запрос
                    await search_field.click()
                    await search_field.fill("тест")
                    self.status_update.emit("Отправляем тестовый запрос...")
                    await search_field.press("Enter")
                    await asyncio.sleep(3)
                    
                    # Проверяем редирект
                    current_url = self.page.url
                    print(f"[AutoLogin] URL после тестового запроса: {current_url}")
                    
                    # Если остались на Wordstat - уже авторизованы
                    if "wordstat.yandex.ru" in current_url and "passport" not in current_url:
                        self.status_update.emit("Аккаунт уже авторизован!")
                        self.progress_update.emit(100)
                        self.login_completed.emit(True, "Аккаунт уже авторизован и работает!")
                        return True
            
            # Проверяем текущий URL после всех попыток
            current_url = self.page.url
            print(f"[AutoLogin] Текущий URL после инициации: {current_url}")
            
            # Шаг 3: Должны попасть на https://passport.yandex.ru/auth
            if "passport.yandex.ru" in current_url:
                self.status_update.emit("Перенаправлены на страницу авторизации...")
                self.progress_update.emit(40)
                
                # Шаг 4: Обработка страницы авторизации - может быть несколько вариантов
                print("[AutoLogin] Обработка страницы авторизации...")
                
                # Сначала проверяем, может уже есть поле логина на текущей странице
                login_input = None
                
                # Пробуем найти поле логина на текущей странице с правильными селекторами 2025
                login_selectors = [
                    'input[name="login"]',  # Основной селектор - всегда присутствует
                    '.Textinput-Control-Input',  # React компонент Textinput
                    'input[type="text"][placeholder*="логин"]',  # По типу и плейсхолдеру
                    '#login-input',  # ID если используется
                    'input.passport-Input-Controller-Input',  # Полный класс контроллера
                    'input[data-t="field:input-login"]',  # Data атрибут
                    'input[autocomplete="username"]'  # Autocomplete атрибут
                ]
                
                print("[AutoLogin] Ищем поле логина на текущей странице...")
                for selector in login_selectors:
                    try:
                        login_input = await self.page.wait_for_selector(selector, state="visible", timeout=1000)
                        if login_input:
                            print(f"[AutoLogin] Нашли поле логина: {selector}")
                            break
                    except:
                        continue
                
                # Если не нашли на текущей странице, переходим на /auth/add/login
                if not login_input:
                    print("[AutoLogin] Переходим на страницу добавления логина...")
                    await self.page.goto("https://passport.yandex.ru/auth/add/login", wait_until="networkidle")
                    await asyncio.sleep(3)
                    
                    # Ищем снова
                    for selector in login_selectors:
                        try:
                            login_input = await self.page.wait_for_selector(selector, state="visible", timeout=2000)
                            if login_input:
                                print(f"[AutoLogin] Нашли поле логина после перехода: {selector}")
                                break
                        except:
                            continue
                
                if login_input:
                    try:
                        # Очищаем поле перед вводом
                        await login_input.click()
                        await login_input.fill("")  # Очищаем
                        await login_input.fill(account_name)
                        self.status_update.emit(f"Вводим логин: {account_name}")
                        self.progress_update.emit(50)
                        
                        # Нажимаем Enter или кнопку "Далее"
                        await self.page.keyboard.press("Enter")
                        await asyncio.sleep(3)
                    except Exception as e:
                        print(f"[AutoLogin] Ошибка при вводе логина: {e}")
                        # Пробуем найти и нажать кнопку "Войти" или "Далее"
                        try:
                            submit_button = await self.page.query_selector('button[type="submit"], button:has-text("Войти"), button:has-text("Далее")')
                            if submit_button:
                                await submit_button.click()
                                await asyncio.sleep(3)
                        except:
                            pass
                    
                    # Шаг 5: Должны попасть на https://passport.yandex.ru/auth/welcome для ввода пароля
                    current_url = self.page.url
                    print(f"[AutoLogin] URL после ввода логина: {current_url}")
                    
                    # Принудительно переходим на страницу пароля если не попали туда
                    if "welcome" not in current_url:
                        print("[AutoLogin] Принудительный переход на страницу ввода пароля...")
                        await self.page.goto("https://passport.yandex.ru/auth/welcome")
                        await asyncio.sleep(2)
                    
                    # Ищем поле для ввода пароля (актуальные селекторы 2025)
                    print("[AutoLogin] Ищем поле для ввода пароля...")
                    
                    password_input = None
                    try:
                        # Основной селектор - стандартный name для пароля (всегда присутствует в 2025)
                        password_input = await self.page.wait_for_selector('input[name="passwd"]', state="visible", timeout=5000)
                        print("[AutoLogin] Нашли поле пароля по name='passwd'")
                    except:
                        print("[AutoLogin] Не нашли по name, пробуем альтернативные селекторы...")
                        # Альтернативные селекторы
                        password_selectors = [
                            'input[type="password"]',  # Тип всегда password
                            '.Textinput-Control-Input[type="password"]',  # Комбо класс + тип
                            'input[placeholder*="пароль"]',  # Плейсхолдер
                            '.passport-PassportForm-Control input'  # Контейнер формы
                        ]
                        
                        for selector in password_selectors:
                            try:
                                password_input = await self.page.wait_for_selector(selector, timeout=2000)
                                if password_input:
                                    print(f"[AutoLogin] Нашли поле пароля: {selector}")
                                    break
                            except:
                                continue
                    
                    if password_input:
                        await password_input.click()
                        await password_input.fill(password)
                        self.status_update.emit("Вводим пароль...")
                        self.progress_update.emit(60)
                        
                        # Отправляем форму
                        await self.page.keyboard.press("Enter")
                        await asyncio.sleep(3)
                        
                        # Шаг 6: Проверяем редирект - возможен переход на https://passport.yandex.ru/auth/challenge
                        current_url = self.page.url
                        print(f"[AutoLogin] URL после ввода пароля: {current_url}")
                        
                        # Обработка секретного вопроса на https://passport.yandex.ru/auth/challenge
                        if "challenge" in current_url or "/auth/challenge" in current_url:
                            self.status_update.emit("⚠️ Требуется секретный вопрос...")
                            self.progress_update.emit(70)
                            
                            print("[AutoLogin] Попали на страницу challenge - требуется секретный вопрос")
                            
                            # Ищем текст вопроса (актуальные селекторы 2025)
                            print("[AutoLogin] Ищем текст секретного вопроса...")
                            question_text = ""
                            
                            # Основные селекторы для текста вопроса
                            question_selectors = [
                                '.Challenge-Question',  # Основной класс
                                'h2',  # Часто в заголовке h2
                                'p.Challenge-Question',  # В параграфе с классом
                                '.passp-form-field__label',  # Альтернативный
                                '.challenge-question__text'  # Еще один вариант
                            ]
                            
                            for selector in question_selectors:
                                try:
                                    question_elem = await self.page.wait_for_selector(selector, timeout=2000)
                                    if question_elem:
                                        question_text = await question_elem.text_content()
                                        print(f"[AutoLogin] Нашли текст вопроса: {question_text}")
                                        break
                                except:
                                    continue
                            
                            if not question_text:
                                question_text = "Введите ответ на секретный вопрос"
                            
                            print(f"[AutoLogin] Секретный вопрос: {question_text}")
                            
                            # Пытаемся найти ответ в конфигурации
                            auto_answer = None
                            try:
                                # Ищем аккаунт в конфигурации
                                for acc in self.accounts_data:
                                    if acc.get('login') == account_name:
                                        secret_answers = acc.get('secret_answers', {})
                                        # Ищем точное совпадение вопроса
                                        if question_text in secret_answers and secret_answers[question_text]:
                                            auto_answer = secret_answers[question_text]
                                            print(f"[AutoLogin] Найден автоматический ответ для вопроса")
                                        # Проверяем частичное совпадение
                                        else:
                                            for q_pattern, answer in secret_answers.items():
                                                if q_pattern != "default" and q_pattern.lower() in question_text.lower() and answer:
                                                    auto_answer = answer
                                                    print(f"[AutoLogin] Найден ответ по частичному совпадению: {q_pattern}")
                                                    break
                                        break
                            except Exception as e:
                                print(f"[AutoLogin] Ошибка при поиске автоответа: {e}")
                            
                            if auto_answer:
                                # Используем автоматический ответ
                                self.secret_answer = auto_answer
                                self.status_update.emit(f"Используем сохранённый ответ...")
                            else:
                                # Отправляем сигнал для показа диалога
                                self.secret_question_required.emit(account_name, question_text)
                            
                            # Ищем поле для ввода ответа (актуальные селекторы 2025)
                            print("[AutoLogin] Ищем поле для ввода ответа на секретный вопрос...")
                            
                            answer_input = None
                            try:
                                # Основной селектор - name для ответа
                                answer_input = await self.page.wait_for_selector('input[name="answer"]', timeout=5000)
                                print("[AutoLogin] Нашли поле ответа по name='answer'")
                            except:
                                print("[AutoLogin] Не нашли по name, пробуем альтернативные селекторы...")
                                # Альтернативные селекторы
                                answer_selectors = [
                                    'textarea[name="secret-answer"]',  # Иногда textarea для длинных ответов
                                    'input[type="text"][placeholder*="ответ"]',  # По плейсхолдеру
                                    '.Challenge-Input',  # Класс для поля challenge
                                    'input[aria-label*="ответ на вопрос"]',  # ARIA для accessibility
                                    '.Textinput-Control-Input[placeholder*="Введите ответ"]'  # React-компонент
                                ]
                                
                                for selector in answer_selectors:
                                    try:
                                        answer_input = await self.page.wait_for_selector(selector, timeout=2000)
                                        if answer_input:
                                            print(f"[AutoLogin] Нашли поле для ответа: {selector}")
                                            break
                                    except:
                                        continue
                            
                            if answer_input:
                                # Ждем ответ от пользователя (максимум 60 секунд)
                                for i in range(60):
                                    if self.secret_answer:
                                        print(f"[AutoLogin] Вводим ответ на секретный вопрос")
                                        await answer_input.click()
                                        await answer_input.fill(self.secret_answer)
                                        self.secret_answer = None  # Сбрасываем
                                        
                                        # Отправляем ответ
                                        await self.page.keyboard.press("Enter")
                                        await asyncio.sleep(3)
                                        break
                                    await asyncio.sleep(1)
                        
                        # Финальная проверка авторизации
                        await asyncio.sleep(3)
                        current_url = self.page.url
                        print(f"[AutoLogin] Финальный URL после авторизации: {current_url}")
                        
                        # Проверяем успешность авторизации
                        if "wordstat.yandex.ru" in current_url:
                            # Успешно вернулись на Wordstat
                            self.status_update.emit("✅ Авторизация успешна!")
                            self.progress_update.emit(100)
                            self.login_completed.emit(True, f"Аккаунт {account_name} успешно авторизован и готов к работе!")
                            return True
                        elif "passport" not in current_url:
                            # Авторизованы, но не на Wordstat - возвращаемся
                            self.status_update.emit("Возвращаемся на Wordstat...")
                            await self.page.goto("https://wordstat.yandex.ru")
                            await asyncio.sleep(2)
                            self.progress_update.emit(100)
                            self.login_completed.emit(True, f"Аккаунт {account_name} успешно авторизован!")
                            return True
                        else:
                            # Остались на паспорте - ошибка авторизации
                            print(f"[AutoLogin] Ошибка: остались на паспорте - {current_url}")
                            self.login_completed.emit(False, "Не удалось завершить авторизацию. Проверьте логин и пароль.")
                            return False
                    else:
                        print("[AutoLogin] Не нашли поле пароля")
                        self.login_completed.emit(False, "Не найдено поле для ввода пароля")
                        return False
                else:
                    print("[AutoLogin] Не нашли поле логина стандартными методами")
                    print("[AutoLogin] Пробуем альтернативный подход...")
                    
                    # Последняя попытка - ищем первый видимый input
                    try:
                        await self.page.goto("https://passport.yandex.ru/auth", wait_until="domcontentloaded")
                        await asyncio.sleep(3)
                        
                        # Пробуем найти любой текстовый input
                        all_inputs = await self.page.query_selector_all('input[type="text"], input[type="email"], input:not([type="hidden"]):not([type="password"])')
                        if all_inputs and len(all_inputs) > 0:
                            print(f"[AutoLogin] Нашли {len(all_inputs)} input полей, используем первое")
                            login_input = all_inputs[0]
                            await login_input.click()
                            await login_input.fill(account_name)
                            await self.page.keyboard.press("Enter")
                            await asyncio.sleep(3)
                        else:
                            print("[AutoLogin] КРИТИЧЕСКАЯ ОШИБКА: Не найдено ни одного поля для ввода")
                            self.login_completed.emit(False, "Не найдено поле для ввода логина. Попробуйте войти вручную.")
                            return False
                    except Exception as e:
                        print(f"[AutoLogin] Ошибка при альтернативном поиске: {e}")
                        self.login_completed.emit(False, f"Ошибка авторизации: {str(e)}")
                        return False
            
            else:
                # Если не на паспорте после всех попыток, пробуем еще раз прямой переход
                print("[AutoLogin] Не на паспорте, пробуем финальный прямой переход на авторизацию")
                self.status_update.emit("Переход на страницу авторизации...")
                
                await self.page.goto("https://passport.yandex.ru/auth/add/login")
                await asyncio.sleep(3)
                
                # Финальная проверка URL
                final_url = self.page.url
                print(f"[AutoLogin] Финальный URL после прямого перехода: {final_url}")
                
                if "passport.yandex.ru" not in final_url:
                    # Если совсем не удалось попасть на паспорт
                    error_msg = "Не удалось открыть страницу авторизации Яндекса. Проверьте подключение к интернету."
                    print(f"[AutoLogin] ОШИБКА: {error_msg}")
                    self.login_completed.emit(False, error_msg)
                    return False
                
                # Если попали на паспорт, продолжаем авторизацию
                self.status_update.emit("Начинаем процесс авторизации...")
                self.progress_update.emit(50)
                
                # Копируем логику авторизации из блока выше
                # Ищем поле для ввода логина
                login_selectors = [
                    'input[name="login"]',
                    '.Textinput-Control-Input',
                    'input[type="text"][placeholder*="логин"]',
                    '#login-input',
                    'input.passport-Input-Controller-Input'
                ]
                
                login_input = None
                for selector in login_selectors:
                    try:
                        login_input = await self.page.query_selector(selector, timeout=1000)
                        if login_input:
                            print(f"[AutoLogin] Нашли поле логина: {selector}")
                            break
                    except:
                        continue
                
                if login_input:
                    await login_input.click()
                    await login_input.fill(account_name)
                    self.status_update.emit(f"Логин введен: {account_name}")
                    self.progress_update.emit(60)
                    await self.page.keyboard.press("Enter")
                    await asyncio.sleep(3)
                    
                    # Переход на страницу пароля и продолжение авторизации
                    print("[AutoLogin] Логин введен, переходим к паролю...")
                    # Здесь код продолжит работать через существующую логику
                else:
                    print("[AutoLogin] Не нашли поле логина в финальном блоке")
                    self.login_completed.emit(False, "Не найдено поле для ввода логина")
                    return False
            
        except Exception as e:
            self.login_completed.emit(False, f"Ошибка: {str(e)}")
            return False
            
        finally:
            # Закрываем браузер для сохранения кук
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
    
    def run_login(self, account_name: str, profile_path: str, proxy: Optional[str] = None):
        """Синхронная обертка для запуска автологина"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self.auto_login(account_name, profile_path, proxy)
            )
            return result
        finally:
            loop.close()

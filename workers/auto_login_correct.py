"""
Правильный автологин согласно документации из папки "новое"
Использует persistent context и правильные селекторы 2025
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from PySide6.QtCore import QObject, Signal

class AutoLoginCorrect(QObject):
    """Правильный воркер для автологина (из папки новое)"""
    
    status_update = Signal(str)
    progress_update = Signal(int)
    secret_question_required = Signal(str, str)
    login_completed = Signal(bool, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.secret_answer = None
        # Загружаем accounts.json
        accounts_file = Path("C:/AI/yandex/configs/accounts.json")
        if accounts_file.exists():
            with open(accounts_file, 'r', encoding='utf-8') as f:
                accounts = json.load(f)
                self.accounts_data = {acc["login"]: acc for acc in accounts}
        else:
            self.accounts_data = {}
    
    def set_secret_answer(self, answer: str):
        self.secret_answer = answer
    
    async def do_login(self, account_name, profile_path, proxy=None):
        """Выполнить автологин по правильной схеме"""
        
        # Получаем пароль
        account_data = self.accounts_data.get(account_name)
        if not account_data:
            self.login_completed.emit(False, f"Аккаунт {account_name} не найден в configs/accounts.json")
            return False
        
        password = account_data["password"]
        
        # Полный путь к профилю
        if not profile_path.startswith("C:"):
            profile_path = f"C:/AI/yandex/{profile_path}"
        Path(profile_path).mkdir(parents=True, exist_ok=True)
        
        self.status_update.emit(f"Запуск Chrome с профилем...")
        self.progress_update.emit(10)
        
        # Парсим прокси
        proxy_config = None
        if proxy and "@" in proxy:
            proxy = proxy.replace("http://", "")
            auth, server = proxy.split("@")
            user, pwd = auth.split(":")
            proxy_config = {
                "server": f"http://{server}",
                "username": user,
                "password": pwd
            }
        
        playwright = await async_playwright().start()
        
        try:
            # ПРАВИЛЬНЫЙ запуск из папки "новое" - launch_persistent_context!
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                channel="chrome",
                headless=False,
                proxy=proxy_config,
                viewport={"width": 1280, "height": 900},
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--start-maximized'
                ],
                locale='ru-RU'
            )
            
            page = context.pages[0] if context.pages else await context.new_page()
            
            self.status_update.emit("Открываем Wordstat...")
            self.progress_update.emit(20)
            
            # Шаг 1: Идем на Wordstat
            await page.goto("https://wordstat.yandex.ru", wait_until="domcontentloaded")
            await asyncio.sleep(3)
            
            # Проверяем - может уже залогинены?
            if "passport.yandex" not in page.url:
                # Пробуем сделать тестовый запрос
                try:
                    input_field = await page.wait_for_selector('input[name="text"]', timeout=3000)
                    if input_field:
                        await input_field.fill("тест")
                        await input_field.press("Enter")
                        await asyncio.sleep(3)
                        
                        # Если остались на wordstat - уже залогинены
                        if "wordstat.yandex" in page.url and "passport" not in page.url:
                            self.status_update.emit("✅ Аккаунт уже авторизован!")
                            self.progress_update.emit(100)
                            self.login_completed.emit(True, "Аккаунт уже авторизован")
                            await context.close()
                            await playwright.stop()
                            return True
                except:
                    pass
            
            # Шаг 2: Переходим на страницу логина (ПРАВИЛЬНЫЙ URL из селекторов 2025)
            self.status_update.emit("Переход на страницу авторизации...")
            self.progress_update.emit(30)
            
            await page.goto("https://passport.yandex.ru/auth/add/login", wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            # Шаг 3: Ищем поле логина (ПРАВИЛЬНЫЕ СЕЛЕКТОРЫ 2025 из файла "38 селекторы логина")
            self.status_update.emit("Ищем поле для ввода логина...")
            
            login_selectors = [
                'input[name="login"]',  # ОСНОВНОЙ - всегда присутствует в 2025!
                '.Textinput-Control-Input',  # React компонент
                'input[type="text"][placeholder*="логин"]',  # По плейсхолдеру
                '#login-input',  # По ID
                'input.passport-Input-Controller-Input'  # Полный класс
            ]
            
            login_input = None
            for selector in login_selectors:
                try:
                    login_input = await page.wait_for_selector(selector, state="visible", timeout=2000)
                    if login_input:
                        print(f"[AutoLogin] ✓ Нашли поле логина: {selector}")
                        break
                except:
                    continue
            
            if not login_input:
                self.login_completed.emit(False, "Не найдено поле для ввода логина")
                await context.close()
                await playwright.stop()
                return False
            
            # Вводим логин
            self.status_update.emit(f"Вводим логин: {account_name}...")
            self.progress_update.emit(40)
            
            await login_input.click()
            await login_input.fill(account_name)
            await page.keyboard.press("Enter")
            await asyncio.sleep(3)
            
            # Шаг 4: Ищем поле пароля (ПРАВИЛЬНЫЕ СЕЛЕКТОРЫ 2025)
            self.status_update.emit("Ищем поле для ввода пароля...")
            self.progress_update.emit(50)
            
            password_selectors = [
                'input[name="passwd"]',  # ОСНОВНОЙ - всегда присутствует!
                'input[type="password"]',  # По типу
                '.Textinput-Control-Input[type="password"]',  # React + тип
                'input[placeholder*="пароль"]'  # По плейсхолдеру
            ]
            
            password_input = None
            for selector in password_selectors:
                try:
                    password_input = await page.wait_for_selector(selector, state="visible", timeout=2000)
                    if password_input:
                        print(f"[AutoLogin] ✓ Нашли поле пароля: {selector}")
                        break
                except:
                    continue
            
            if not password_input:
                self.login_completed.emit(False, "Не найдено поле для ввода пароля")
                await context.close()
                await playwright.stop()
                return False
            
            # Вводим пароль
            self.status_update.emit("Вводим пароль...")
            self.progress_update.emit(60)
            
            await password_input.click()
            await password_input.fill(password)
            await page.keyboard.press("Enter")
            await asyncio.sleep(4)
            
            # Шаг 5: Проверяем секретный вопрос (challenge)
            current_url = page.url
            if "challenge" in current_url:
                self.status_update.emit("Требуется секретный вопрос...")
                self.progress_update.emit(70)
                
                # Ищем текст вопроса
                question_selectors = [
                    '.Challenge-Question',
                    'h2',
                    'p.Challenge-Question'
                ]
                
                question_text = "Введите ответ на секретный вопрос"
                for selector in question_selectors:
                    try:
                        elem = await page.wait_for_selector(selector, timeout=2000)
                        if elem:
                            question_text = await elem.text_content()
                            break
                    except:
                        continue
                
                # Запрашиваем ответ у пользователя
                self.secret_question_required.emit(account_name, question_text)
                
                # Ждем ответа (макс 60 сек)
                for i in range(60):
                    if self.secret_answer:
                        break
                    await asyncio.sleep(1)
                
                if not self.secret_answer:
                    self.login_completed.emit(False, "Таймаут ожидания ответа на секретный вопрос")
                    await context.close()
                    await playwright.stop()
                    return False
                
                # Ищем поле для ответа
                answer_selectors = [
                    'input[name="answer"]',
                    '.Challenge-Input',
                    'input[type="text"][placeholder*="ответ"]'
                ]
                
                answer_input = None
                for selector in answer_selectors:
                    try:
                        answer_input = await page.wait_for_selector(selector, timeout=2000)
                        if answer_input:
                            break
                    except:
                        continue
                
                if answer_input:
                    await answer_input.click()
                    await answer_input.fill(self.secret_answer)
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(3)
            
            # Шаг 6: Проверяем успешность
            await asyncio.sleep(2)
            final_url = page.url
            
            if "wordstat.yandex" in final_url or "passport" not in final_url:
                self.status_update.emit("✅ Авторизация успешна!")
                self.progress_update.emit(100)
                self.login_completed.emit(True, "Аккаунт успешно авторизован")
                await context.close()
                await playwright.stop()
                return True
            else:
                self.login_completed.emit(False, "Не удалось завершить авторизацию")
                await context.close()
                await playwright.stop()
                return False
                
        except Exception as e:
            self.login_completed.emit(False, f"Ошибка: {str(e)}")
            try:
                await context.close()
                await playwright.stop()
            except:
                pass
            return False
    
    def run_login(self, account_name, profile_path, proxy=None):
        """Синхронная обертка"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.do_login(account_name, profile_path, proxy))
        finally:
            loop.close()

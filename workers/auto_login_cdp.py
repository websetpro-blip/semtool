"""
CDP Автологин для Яндекс Wordstat
Использует Chrome DevTools Protocol для стабильной авторизации
Основано на решении из файла yandex/новое/39
"""
import subprocess
import asyncio
import json
import time
import re
from pathlib import Path
from playwright.async_api import async_playwright
from PySide6.QtCore import QObject, Signal


class AutoLoginCDP(QObject):
    """CDP автологин с обработкой всех форм авторизации Яндекса"""
    
    status_update = Signal(str)
    progress_update = Signal(int)
    secret_question_required = Signal(str, str)
    login_completed = Signal(bool, str)
    
    def __init__(self):
        super().__init__()
        self.secret_answer = None
        self.chrome_process = None
        
    def set_secret_answer(self, answer):
        """Установить ответ на секретный вопрос"""
        self.secret_answer = answer
        
    async def do_login(self, account_name, profile_path, proxy=None):
        """Главная функция CDP автологина"""
        try:
            self.status_update.emit(f"Запуск автологина для {account_name}...")
            self.progress_update.emit(10)
            
            # Используем Playwright с правильной обработкой прокси
            async with async_playwright() as p:
                # Формируем параметры прокси для Playwright
                proxy_config = None
                if proxy:
                    # Парсим прокси формата: ip:port@user:pass или http://user:pass@ip:port
                    if "@" in proxy:
                        if proxy.startswith("http://"):
                            proxy = proxy.replace("http://", "")
                        
                        # Разбираем на части
                        if ":" in proxy.split("@")[1] and ":" in proxy.split("@")[0]:
                            # Формат: ip:port@user:pass
                            server_part, auth_part = proxy.split("@")
                            host, port = server_part.split(":")
                            username, password = auth_part.split(":")
                        else:
                            # Формат: user:pass@ip:port
                            auth_part, server_part = proxy.split("@")
                            username, password = auth_part.split(":")
                            host, port = server_part.split(":")
                        
                        proxy_config = {
                            "server": f"http://{host}:{port}",
                            "username": username,
                            "password": password
                        }
                        self.status_update.emit(f"Используется прокси {host}:{port}")
                    else:
                        proxy_config = {"server": f"http://{proxy}"}
                
                # Запускаем Chrome с persistent context и прокси
                browser_args = [
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-blink-features=AutomationControlled"
                ]
                
                # НЕ используем флаг --proxy-server! Playwright сам обработает
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=profile_path,
                    channel="chrome",  # Используем установленный Chrome
                    proxy=proxy_config,  # Прокси передаем через Playwright!
                    headless=False,
                    args=browser_args,
                    ignore_default_args=["--enable-automation"]
                )
                
                # Создаем новую страницу или используем существующую
                if context.pages:
                    page = context.pages[0]
                else:
                    page = await context.new_page()
                
                # Переходим на страницу авторизации
                await page.goto("https://passport.yandex.ru/auth?retpath=https://wordstat.yandex.ru")
                await page.wait_for_load_state("domcontentloaded")
                # Проверка авторизации
                self.status_update.emit("Проверка авторизации...")
                self.progress_update.emit(30)
                
                current_url = page.url
                
                # Если уже на wordstat - авторизован
                if "wordstat.yandex" in current_url:
                    self.status_update.emit(f"✅ {account_name} уже авторизован!")
                    self.progress_update.emit(100)
                    self.login_completed.emit(True, "Аккаунт уже авторизован")
                    return True
                
                # Если на ya.ru или id.yandex - тоже авторизован
                if any(x in current_url for x in ["ya.ru", "id.yandex.ru"]):
                    self.status_update.emit("Авторизован, переход на Wordstat...")
                    await page.goto("https://wordstat.yandex.ru")
                    self.progress_update.emit(100)
                    self.login_completed.emit(True, "Успешная авторизация")
                    return True
                    
                    # Ждем форму логина
                    await page.wait_for_url(re.compile(r"passport\.yandex\.(ru|com|by|kz|ua)/auth"), 
                                           timeout=20000)
                    
                    # Определяем тип формы (как в решении из файла 39)
                    is_new_form = await page.locator("#passp-field-login").count() > 0
                    is_legacy = not is_new_form and await page.get_by_role(
                        "textbox", name=re.compile("логин", re.I)
                    ).count() > 0
                    
                    # Загружаем данные аккаунта
                    config_path = Path("C:/AI/yandex/configs/accounts.json")
                    if config_path.exists():
                        with open(config_path, 'r', encoding='utf-8') as f:
                            accounts = json.load(f)
                            account_data = next((a for a in accounts if a["login"] == account_name), None)
                            if not account_data:
                                raise Exception(f"Аккаунт {account_name} не найден в конфиге")
                    else:
                        raise Exception("Файл accounts.json не найден")
                    
                    password = account_data["password"]
                    secret = account_data.get("secret", "")
                    
                    # НОВАЯ ФОРМА (два шага)
                    if is_new_form:
                        self.status_update.emit("Обнаружена новая форма, ввод логина...")
                        self.progress_update.emit(40)
                        
                        # Вводим логин
                        await page.fill("#passp-field-login", account_name)
                        await page.locator('button[type=submit], button:has-text("Войти")').click()
                        
                        # Ждем перехода на ввод пароля
                        await page.wait_for_url(
                            re.compile(r"auth/(password|challenge|welcome)"), 
                            timeout=10000
                        )
                        
                        # Вводим пароль если есть поле
                        if await page.locator("#passp-field-passwd").count():
                            self.status_update.emit("Ввод пароля...")
                            self.progress_update.emit(60)
                            await page.fill("#passp-field-passwd", password)
                            await page.locator('button[type=submit], button:has-text("Войти")').click()
                    
                    # ЛЕГАСИ ФОРМА (два поля сразу)
                    elif is_legacy:
                        self.status_update.emit("Обнаружена легаси форма...")
                        self.progress_update.emit(40)
                        
                        form = page.locator("form")
                        await form.get_by_role("textbox", name=re.compile("логин", re.I)).fill(account_name)
                        await form.locator('input[type="password"]').fill(password)
                        await form.get_by_role("button", name=re.compile("войти", re.I)).click()
                    
                    # Ждем результата
                    self.status_update.emit("Проверка результата авторизации...")
                    self.progress_update.emit(70)
                    await asyncio.sleep(2)
                    
                    # Проверяем challenge (секретный вопрос в iframe)
                    current_url = page.url
                    has_challenge_frame = await page.locator(
                        'iframe[src*="challenge"], iframe[name*="passp:challenge"]'
                    ).count() > 0
                    
                    if has_challenge_frame or "auth/challenge" in current_url:
                        self.status_update.emit("Обнаружен секретный вопрос...")
                        self.progress_update.emit(80)
                        
                        # Работаем с iframe
                        ch_frame = page.frame_locator('iframe[src*="challenge"], iframe[name*="passp:challenge"]')
                        
                        # Получаем текст вопроса
                        question_elem = ch_frame.locator('.challenge-form__question')
                        if await question_elem.count() > 0:
                            question_text = await question_elem.inner_text()
                        else:
                            question_text = "Введите ответ на секретный вопрос"
                        
                        # Если есть сохраненный ответ - используем
                        if secret:
                            answer = secret
                        else:
                            # Запрашиваем у пользователя
                            self.secret_question_required.emit(question_text, account_name)
                            
                            # Ждем ответа
                            for _ in range(60):  # 60 секунд на ответ
                                if self.secret_answer:
                                    answer = self.secret_answer
                                    self.secret_answer = None
                                    break
                                await asyncio.sleep(1)
                            else:
                                raise Exception("Не получен ответ на секретный вопрос")
                        
                        # Вводим ответ
                        answer_input = ch_frame.get_by_role("textbox").or_(
                            ch_frame.locator('input[name="answer"]')
                        )
                        await answer_input.fill(answer)
                        await ch_frame.get_by_role("button", name=re.compile("Продолжить|Continue", re.I)).click()
                    
                    # Финальная проверка
                    await asyncio.sleep(3)
                    current_url = page.url
                    
                    # Успешная авторизация - редирект на ya.ru, id.yandex или wordstat
                    if any(x in current_url for x in ["ya.ru", "id.yandex", "wordstat.yandex"]):
                        self.status_update.emit(f"✅ Успешная авторизация {account_name}!")
                        
                        # Переходим на wordstat если не там
                        if "wordstat.yandex" not in current_url:
                            await page.goto("https://wordstat.yandex.ru")
                            await page.wait_for_load_state("networkidle")
                        
                        self.progress_update.emit(100)
                        self.login_completed.emit(True, "Успешная авторизация")
                        return True
                    else:
                        raise Exception(f"Неизвестная страница после авторизации: {current_url}")
                        
                except Exception as e:
                    self.status_update.emit(f"❌ Ошибка: {str(e)}")
                    self.login_completed.emit(False, str(e))
                    return False
                finally:
                    # Закрываем браузер но оставляем Chrome запущенным
                    try:
                        await browser.close()
                    except:
                        pass
                        
        except Exception as e:
            self.status_update.emit(f"❌ Критическая ошибка: {str(e)}")
            self.login_completed.emit(False, str(e))
            return False

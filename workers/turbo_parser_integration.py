"""
ТУРБО ПАРСЕР ИНТЕГРАЦИЯ ДЛЯ SEMTOOL
Интегрирует наш парсер 195.9 фраз/мин в KeySet
Основан на parser_final_130plus.py + рекомендации GPT
"""

import asyncio
import time
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import quote

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import sqlite3

from ..core.db import SessionLocal
from ..core.models import Account
from .visual_browser_manager import VisualBrowserManager, BrowserStatus
from .auto_auth_handler import AutoAuthHandler


class AIMDController:
    """AIMD регулятор скорости для избежания банов"""
    
    def __init__(self):
        self.delay_ms = 50  # начальная задержка (уменьшена для скорости)
        self.min_delay = 30
        self.max_delay = 300
        self.success_count = 0
        self.error_count = 0
        
    def on_success(self):
        """При успехе уменьшаем задержку"""
        self.success_count += 1
        if self.success_count >= 10:
            self.delay_ms = max(self.min_delay, self.delay_ms - 10)
            self.success_count = 0
            
    def on_error(self):
        """При ошибке увеличиваем задержку"""
        self.error_count += 1
        self.delay_ms = min(self.max_delay, self.delay_ms * 1.5)
        
    def get_delay(self):
        """Получить текущую задержку в секундах"""
        return self.delay_ms / 1000.0


class TurboWordstatParser:
    """
    Турбо парсер Wordstat - 195.9 фраз/мин
    Использует технологии из наших лучших парсеров
    """
    
    def __init__(self, account: Optional[Account] = None, headless: bool = False, visual_mode: bool = True):
        self.account = account
        self.headless = headless
        self.visual_mode = visual_mode  # Визуальный режим с несколькими браузерами
        self.browser = None
        self.context = None
        self.pages = []  # мульти-табы
        self.results = {}
        self.aimd = AIMDController()
        self.num_tabs = 10  # количество вкладок для обработки (боевой режим)
        self.num_browsers = 1  # количество видимых браузеров
        self.visual_manager = None  # Менеджер визуальных браузеров
        self.db_path = Path("C:/AI/yandex/keyset/data/keyset.db")
        self.auth_handler = AutoAuthHandler()  # Обработчик авторизации
        
        # Загружаем данные авторизации из accounts.json если нет в аккаунте
        if self.account:
            self._load_auth_data()
        
        # Статистика
        self.total_processed = 0
        self.total_errors = 0
        self.start_time = None
    
    def _load_auth_data(self):
        """Загружаем данные авторизации из accounts.json"""
        try:
            accounts_json_path = Path("C:/AI/yandex/keyset/configs/accounts.json")
            if not accounts_json_path.exists():
                accounts_json_path = Path("C:/AI/yandex/configs/accounts.json")
            if not accounts_json_path.exists():
                accounts_json_path = Path("C:/AI/accounts.json")
            
            if accounts_json_path.exists():
                with open(accounts_json_path, 'r', encoding='utf-8') as f:
                    accounts_data = json.load(f)
                
                # Ищем данные для нашего аккаунта
                for acc_data in accounts_data:
                    if acc_data.get('login') == self.account.name:
                        # Заполняем данные если их нет
                        if not hasattr(self.account, 'password') or not self.account.password:
                            self.account.password = acc_data.get('password', '')
                        if not hasattr(self.account, 'secret_answer') or not self.account.secret_answer:
                            self.account.secret_answer = acc_data.get('secret_answer', '')
                        if not hasattr(self.account, 'login') or not self.account.login:
                            self.account.login = acc_data.get('login', self.account.name)
                        print(f"[AUTH] Загружены данные для {self.account.name}")
                        break
        except Exception as e:
            print(f"[AUTH] Ошибка загрузки accounts.json: {e}")
        
    async def init_browser(self):
        """Инициализация браузера - ПОДКЛЮЧЕНИЕ через CDP как в инструкциях"""
        self.playwright = await async_playwright().start()
        
        # КРИТИЧНО из инструкций: СНАЧАЛА нужно запустить Chrome с CDP!
        print("[TURBO] Пытаюсь подключиться к Chrome через CDP на порту 9222...")
        print("[TURBO] Если не работает, запустите START_CHROME_CDP.bat!")
        
        # Пробуем подключиться к существующему Chrome через CDP
        try:
            self.browser = await self.playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
            self.context = self.browser.contexts[0]
            print("[TURBO] Успешно подключен к Chrome через CDP!")
            
            # Проверяем что есть открытые вкладки
            if not self.context.pages:
                print("[TURBO] Нет открытых вкладок, создаю новую...")
                page = await self.context.new_page()
                await page.goto("https://wordstat.yandex.ru", wait_until="domcontentloaded")
            else:
                print(f"[TURBO] Найдено {len(self.context.pages)} открытых вкладок")
        except Exception as e:
            print(f"\n[ERROR] Не удалось подключиться к Chrome через CDP!")
            print(f"[ERROR] Ошибка: {e}")
            print("\nПожалуйста:")
            print("1. Запустите START_CHROME_CDP.bat")
            print("2. Убедитесь что Chrome открылся")
            print("3. Попробуйте снова\n")
            
            # Проверяем, может Chrome не запущен?
            import subprocess
            try:
                # Пытаемся автоматически запустить Chrome
                print("[TURBO] Пытаюсь запустить Chrome с CDP...")
                chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                if self.account and getattr(self.account, "profile_path", None):
                    profile_path = Path(self.account.profile_path)
                elif self.account and getattr(self.account, "name", None):
                    profile_path = Path(f"C:/AI/yandex/.profiles/{self.account.name}")
                else:
                    profile_path = Path("C:/AI/yandex/.profiles/default")
                if not profile_path.is_absolute():
                    profile_path = Path("C:/AI/yandex") / profile_path
                profile_path_str = str(profile_path).replace("\\", "/")
                
                subprocess.Popen([
                    chrome_path,
                    f"--remote-debugging-port=9222",
                    f"--user-data-dir={profile_path_str}",
                    "https://wordstat.yandex.ru"
                ])
                
                # Ждем запуска Chrome
                await asyncio.sleep(3)
                
                # Повторная попытка подключения
                self.browser = await self.playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
                self.context = self.browser.contexts[0]
                print("[TURBO] Chrome запущен и подключен!")
            except Exception as e2:
                print(f"[ERROR] Не удалось запустить Chrome автоматически: {e2}")
                raise Exception("Не удалось подключиться к Chrome. Запустите START_CHROME_CDP.bat")

            
            # При CDP подключении профиль уже используется запущенным Chrome
    
    async def setup_tabs(self):
        """Настройка всех вкладок СРАЗУ (из финального парсера)"""
        print(f"[TURBO] Подготовка {self.num_tabs} вкладок...")
        
        existing_pages = self.context.pages
        
        # КРИТИЧНО: Создаем ВСЕ недостающие вкладки СРАЗУ
        print(f"[TURBO] Существующих вкладок: {len(existing_pages)}, нужно: {self.num_tabs}")
        
        for i in range(len(existing_pages), self.num_tabs):
            print(f"[TURBO] Создаю вкладку {i+1}...")
            page = await self.context.new_page()
            existing_pages.append(page)
        
        self.pages = existing_pages[:self.num_tabs]
        self.page_mapping = {}
        
        print(f"[TURBO] Загружаем Wordstat на {len(self.pages)} вкладках...")
        
        # Загружаем Wordstat на ВСЕХ вкладках
        for i, page in enumerate(self.pages):
            self.page_mapping[i] = page
            
            if "wordstat.yandex.ru" not in page.url:
                print(f"[TURBO] Tab {i}: Открываю Wordstat...")
                try:
                    await page.goto("https://wordstat.yandex.ru", timeout=15000)
                    print(f"[TURBO] Tab {i}: Wordstat открыт")
                except Exception as e:
                    print(f"[TURBO] Tab {i}: Ошибка: {str(e)[:50]}")
                
                # Пауза между загрузками чтобы не триггерить защиту
                await asyncio.sleep(2)
            else:
                print(f"[TURBO] Tab {i}: Wordstat уже открыт")
        
        print(f"[TURBO] ВСЕ {len(self.pages)} вкладок готовы к работе!")
        
        # Настраиваем перехват ответов на всех вкладках
        for i, page in enumerate(self.pages):
            page.on("response", lambda response, tab_id=i: asyncio.create_task(
                self.handle_response(response, tab_id)
            ))
    
    async def wait_wordstat_ready(self, page):
        """Ожидание полной загрузки Wordstat (из файла 46)"""
        try:
            # 1) Базовая загрузка документа
            await page.wait_for_load_state('domcontentloaded', timeout=30000)
            
            # 2) Проверяем, не перебросило ли на паспорт
            current_url = page.url
            if "passport.yandex" in current_url or "passport.ya.ru" in current_url:
                print(f"[AUTH] Обнаружена страница авторизации!")
                
                # Попытаемся авторизоваться
                if self.auth_handler and self.account:
                    account_data = {
                        'login': self.account.login if hasattr(self.account, 'login') else self.account.name,
                        'password': self.account.password if hasattr(self.account, 'password') else '',
                        'secret_answer': self.account.secret_answer if hasattr(self.account, 'secret_answer') else ''
                    }
                    
                    success = await self.auth_handler.handle_auth_redirect(page, account_data)
                    if success:
                        print(f"[AUTH] Авторизация успешна")
                        # После авторизации переходим на wordstat
                        await page.goto("https://wordstat.yandex.ru", wait_until="domcontentloaded", timeout=30000)
                    else:
                        print(f"[AUTH] Ошибка авторизации")
            
            # 3) Ждём URL Wordstat
            await page.wait_for_url("**/wordstat.yandex.ru/**", timeout=30000)
            
            # 4) Дождаться сетевой активности для SPA
            try:
                await page.wait_for_load_state('networkidle', timeout=15000)
            except:
                pass  # Может не дождаться networkidle, это не критично
            
            # 5) Явный DOM-гейт - ждём поле поиска
            search_selectors = [
                'input[type="search"]',
                '[role="searchbox"]',
                'input.b-form-input__input',
                'input[name="text"]'
            ]
            
            for selector in search_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    break
                except:
                    continue
            
        except Exception as e:
            print(f"[WAIT] Ошибка ожидания загрузки Wordstat: {e}")
    
    async def handle_response(self, response, tab_id):
        """Перехват XHR ответов от Wordstat API"""
        try:
            if "/wordstat/api" in response.url and response.status == 200:
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    data = await response.json()
                    
                    # Извлекаем данные о частотности
                    if 'data' in data and 'totalValue' in data['data']:
                        frequency = data['data']['totalValue']
                        
                        # Получаем запрос из request body
                        request_body = response.request.post_data
                        if request_body:
                            request_data = json.loads(request_body)
                            query = request_data.get("searchValue", "").strip()
                            
                            if query:
                                self.results[query] = frequency
                                self.total_processed += 1
                                self.aimd.on_success()
                                print(f"[Tab {tab_id}] OK {query} = {frequency:,}")
        except Exception as e:
            pass  # Игнорируем ошибки парсинга ответов
    
    async def process_tab_worker(self, page, phrases, tab_id):
        """Воркер для обработки фраз на одной вкладке (рабочая версия из parse_5_accounts_cdp.py)"""
        tab_results = []
        results_lock = asyncio.Lock()
        
        # Настраиваем обработчик ответов для перехвата частотностей
        async def handle_response(response):
            """Перехватываем ответы API и извлекаем частотности"""
            if "/wordstat/api" in response.url and response.status == 200:
                try:
                    data = await response.json()
                    
                    # Извлекаем частотность из структуры данных
                    frequency = None
                    if 'data' in data and isinstance(data['data'], dict) and 'totalValue' in data['data']:
                        frequency = data['data']['totalValue']
                    elif 'totalValue' in data:
                        frequency = data['totalValue']
                    
                    if frequency is not None:
                        # Получаем маску из тела POST запроса
                        post_data = response.request.post_data
                        if post_data:
                            request_data = json.loads(post_data)
                            phrase = request_data.get("searchValue", "").strip()
                            
                            if phrase:
                                async with results_lock:
                                    self.results[phrase] = frequency
                                    tab_results.append({'query': phrase, 'frequency': frequency})
                                    self.total_processed += 1
                                    self.aimd.on_success()
                                print(f"[Tab {tab_id}] OK: {phrase} = {frequency:,} показов")
                except Exception as e:
                    pass  # Игнорируем ошибки парсинга
        
        # Подключаем обработчик к странице
        page.on("response", handle_response)
        
        # Загружаем и ждем полной готовности Wordstat
        if "wordstat.yandex.ru" not in page.url:
            print(f"[Tab {tab_id}] Открываю Wordstat...")
            try:
                await page.goto("https://wordstat.yandex.ru", timeout=15000)
                # Ждем полной загрузки страницы
                await page.wait_for_load_state('domcontentloaded')
                # networkidle может долго ждать, используем с малым таймаутом
                try:
                    await page.wait_for_load_state('networkidle', timeout=3000)
                except:
                    pass  # Не критично если не дождались
            except Exception as e:
                print(f"[Tab {tab_id}] Ошибка при открытии: {e}")
                return tab_results
        
        # Убеждаемся что поле ввода доступно перед началом
        print(f"[Tab {tab_id}] Проверяю готовность страницы...")
        try:
            await page.wait_for_selector('input[placeholder*="слово"], input[name="text"]', timeout=10000)
            print(f"[Tab {tab_id}] Wordstat готов к работе!")
        except:
            print(f"[Tab {tab_id}] Поле ввода не найдено, страница не готова")
            return tab_results
        
        # Обрабатываем каждую фразу
        for phrase in phrases:
            if phrase in self.results:
                continue
            
            try:
                # Ищем поле ввода с разными селекторами
                input_field = None
                selectors = [
                    'input[name="text"]',
                    'input[placeholder*="слово"]',
                    '.b-form-input__input',
                    'input[type="text"]'
                ]
                
                for selector in selectors:
                    try:
                        if await page.locator(selector).count() > 0:
                            input_field = page.locator(selector).first
                            break
                    except:
                        continue
                
                if input_field:
                    # Очищаем и вводим фразу
                    await input_field.clear()
                    await input_field.fill(phrase)
                    await input_field.press("Enter")
                    
                    # Ждем ответ (минимальная задержка)
                    await asyncio.sleep(0.5)
                else:
                    print(f"[Tab {tab_id}] Не найдено поле ввода для '{phrase}'")
                    
            except Exception as e:
                print(f"[Tab {tab_id}] Ошибка для '{phrase}': {str(e)[:50]}")
                self.aimd.on_error()
                
                # При ошибке пробуем перезагрузить страницу
                try:
                    await page.reload()
                    await asyncio.sleep(2)
                except:
                    pass
        
        # Даем время на последние ответы
        await asyncio.sleep(2)
        
        print(f"[Tab {tab_id}] Завершено: обработано {len(tab_results)} фраз")
        return tab_results
    
    async def parse_batch_visual(self, queries: List[str], region: int = 225):
        """Парсинг батча фраз в визуальном режиме с несколькими браузерами"""
        self.start_time = time.time()
        
        # Создаем визуальный менеджер
        self.visual_manager = VisualBrowserManager(num_browsers=self.num_browsers)
        
        # Подготавливаем аккаунты для браузеров - БЕРЕМ ИЗ БАЗЫ ДАННЫХ!
        accounts = []
        
        # Импортируем сервис аккаунтов для получения данных из БД
        from ..services import accounts as account_service
        
        # Получаем все аккаунты из базы данных
        all_accounts_db = account_service.list_accounts()
        
        # Фильтруем demo_account и конвертируем в нужный формат
        all_accounts = []
        for acc in all_accounts_db:
            if acc.name != "demo_account":
                # Берем профиль из БД!
                profile_path_obj = Path(acc.profile_path or f".profiles/{acc.name}")
                if not profile_path_obj.is_absolute():
                    profile_path_obj = Path("C:/AI/yandex") / profile_path_obj
                profile_path = str(profile_path_obj).replace("\\", "/")
                
                all_accounts.append({
                    "name": acc.name,
                    "profile_path": profile_path,
                    "proxy": acc.proxy
                })
        
        if self.account:
            # Добавляем основной аккаунт первым
            profile_path_obj = Path(self.account.profile_path or f".profiles/{self.account.name}")
            if not profile_path_obj.is_absolute():
                profile_path_obj = Path("C:/AI/yandex") / profile_path_obj
            profile_path = str(profile_path_obj).replace("\\", "/")
            
            accounts.append({
                "name": self.account.name,
                "profile_path": profile_path,
                "proxy": self.account.proxy
            })
        
        # Добавляем остальные аккаунты до нужного количества браузеров
        for acc in all_accounts:
            if len(accounts) >= self.num_browsers:
                break
            # Пропускаем уже добавленный основной аккаунт
            if not any(a["name"] == acc["name"] for a in accounts):
                accounts.append(acc)
        
        try:
            # Запускаем браузеры в видимом режиме
            print(f"\n[VISUAL] Запуск {self.num_browsers} браузеров...")
            await self.visual_manager.start_all_browsers(accounts)
            
            # Ждем пока пользователь залогинится
            print("\n[!] ВАЖНО: Залогиньтесь в каждом открытом браузере!")
            print("После логина парсинг начнется автоматически.\n")
            
            logged_in = await self.visual_manager.wait_for_all_logins(timeout=300)
            
            if not logged_in:
                print("[VISUAL] Ошибка: не удалось залогиниться")
                return []
            
            # Минимизируем браузеры для фоновой работы
            print("\n[VISUAL] Минимизация браузеров...")
            await self.visual_manager.minimize_all_browsers()
            
            # Парсим фразы
            print(f"\n[VISUAL] Начинаем парсинг {len(queries)} фраз...")
            results_dict = await self.visual_manager.parse_batch_parallel(queries)
            
            # Преобразуем результаты
            results = []
            for phrase, freq in results_dict.items():
                results.append({
                    'query': phrase,
                    'frequency': freq,
                    'timestamp': datetime.now().isoformat()
                })
                self.total_processed += 1
            
            # Сохраняем в БД
            await self.save_to_db(results)
            
            # Статистика
            elapsed = time.time() - self.start_time
            speed = len(results) / elapsed * 60 if elapsed > 0 else 0
            
            print(f"\n{'='*70}")
            print(f"   РЕЗУЛЬТАТЫ ВИЗУАЛЬНОГО ПАРСИНГА")
            print(f"{'='*70}")
            print(f"  Время: {elapsed:.1f} сек")
            print(f"  Обработано: {len(results)}/{len(queries)}")
            print(f"  Успех: {len(results)/len(queries)*100:.1f}%")
            print(f"  СКОРОСТЬ: {speed:.1f} фраз/мин")
            print(f"  Браузеров использовано: {self.num_browsers}")
            print(f"{'='*70}")
            
            return results
            
        finally:
            if self.visual_manager:
                await self.visual_manager.close_all()
    
    async def parse_batch(self, queries: List[str], region: int = 225):
        """Парсинг батча фраз с мульти-табами"""
        # Если включен визуальный режим - используем visual manager
        if self.visual_mode and not self.headless:
            return await self.parse_batch_visual(queries, region)
        
        self.start_time = time.time()
        all_results = []  # Инициализируем результаты до try
        
        try:
            # Инициализация
            await self.init_browser()
            await self.setup_tabs()
        
            # Распределяем фразы по табам
            tab_phrases = [[] for _ in range(self.num_tabs)]
            for i, phrase in enumerate(queries):
                tab_idx = i % self.num_tabs
                tab_phrases[tab_idx].append(phrase)
            
            print(f"[TURBO] Распределено {len(queries)} фраз по {self.num_tabs} табам")
            
            # Запускаем воркеры параллельно
            tasks = []
            for i in range(self.num_tabs):
                if tab_phrases[i]:
                    page = self.pages[i]
                    tasks.append(self.process_tab_worker(page, tab_phrases[i], i))
            
            # Ждем завершения всех воркеров
            results = await asyncio.gather(*tasks, return_exceptions=True)  # return_exceptions чтобы не падать на ошибках
            
            # Собираем все результаты
            for tab_results in results:
                if tab_results and not isinstance(tab_results, Exception):
                    all_results.extend(tab_results)
            
            # Статистика
            elapsed = time.time() - self.start_time
            speed = len(all_results) / elapsed * 60 if elapsed > 0 else 0
            
            print(f"\n{'='*70}")
            print(f"   РЕЗУЛЬТАТЫ ТУРБО ПАРСИНГА")
            print(f"{'='*70}")
            print(f"  Время: {elapsed:.1f} сек")
            print(f"  Обработано: {len(all_results)}/{len(queries)}")
            print(f"  Успех: {len(all_results)/len(queries)*100:.1f}%" if queries else "0%")
            print(f"  СКОРОСТЬ: {speed:.1f} фраз/мин")
            print(f"{'='*70}")
            
        except Exception as e:
            print(f"[TURBO] КРИТИЧЕСКАЯ ОШИБКА в parse_batch: {e}")
            import traceback
            traceback.print_exc()
        
        return all_results
    
    async def save_to_db(self, results: List[Dict]):
        """Сохранение результатов в БД KeySet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for result in results:
            cursor.execute("""
                INSERT OR REPLACE INTO freq_results 
                (mask, region, freq_total, freq_exact, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                result['query'],
                225,  # регион РФ
                result['frequency'],
                result['frequency'],
                'ok',
                result['timestamp']
            ))
        
        conn.commit()
        conn.close()
        print(f"[TURBO] Сохранено {len(results)} результатов в БД")
    
    async def close(self):
        """Отключение от CDP браузера (НЕ закрываем Chrome - он остается работать)"""
        try:
            # При CDP подключении мы НЕ закрываем Chrome!
            # Просто отключаемся
            print("[TURBO] Отключаюсь от Chrome CDP...")
            
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            
            print("[TURBO] Отключение завершено. Chrome остается работать для следующих запусков.")
        except Exception as e:
            print(f"[TURBO] Ошибка при отключении: {e}")


# Дополнительные модули из рекомендаций GPT

class ForecastParser:
    """Парсер прогноза бюджета через web интерфейс Директа"""
    
    async def parse_forecast(self, phrases: List[str], region: int = 225):
        """Получить прогноз бюджета для фраз"""
        # TODO: Реализовать парсинг страницы прогноза Директа
        pass


class SuggestParser:
    """Парсер подсказок Яндекса для расширения семантики"""
    
    async def get_suggestions(self, seed_phrase: str) -> List[str]:
        """Получить подсказки для фразы"""
        # TODO: Использовать API подсказок Яндекса
        pass


class PhraseClusterer:
    """Кластеризация фраз и генерация минус-слов"""
    
    def cluster_phrases(self, phrases: List[str], threshold: float = 0.6):
        """Кластеризация похожих фраз"""
        # TODO: Реализовать через pymorphy2 + TF-IDF
        pass
    
    def generate_minus_words(self, clusters: Dict):
        """Генерация кросс-минус слов между кластерами"""
        # TODO: Найти пересечения между кластерами
        pass


# Главная функция для интеграции в KeySet
async def run_turbo_parser(queries: List[str], account: Optional[Account] = None, headless: bool = False):
    """
    Запуск турбо парсера из GUI KeySet
    
    Args:
        queries: список фраз для парсинга
        account: аккаунт с профилем и прокси
        headless: фоновый режим
    
    Returns:
        Список результатов с частотностями
    """
    parser = TurboWordstatParser(account=account, headless=headless)
    
    try:
        results = await parser.parse_batch(queries)
        await parser.save_to_db(results)
        return results
    finally:
        await parser.close()


if __name__ == "__main__":
    # Тестовый запуск
    test_queries = [
        "купить квартиру москва",
        "ремонт квартир",
        "заказать пиццу",
        "доставка еды",
        "такси москва"
    ]
    
    asyncio.run(run_turbo_parser(test_queries, headless=False))

"""
ТУРБО ПАРСЕР ИНТЕГРАЦИЯ ДЛЯ SEMTOOL
Интегрирует наш парсер 195.9 фраз/мин в SemTool
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
        self.delay_ms = 150  # начальная задержка
        self.min_delay = 50
        self.max_delay = 500
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
        self.num_tabs = 10  # количество вкладок для параллельного парсинга
        self.num_browsers = 3  # количество видимых браузеров
        self.visual_manager = None  # Менеджер визуальных браузеров
        self.db_path = Path("C:/AI/yandex/semtool/data/semtool.db")
        self.auth_handler = AutoAuthHandler()  # Обработчик авторизации
        
        # Статистика
        self.total_processed = 0
        self.total_errors = 0
        self.start_time = None
        
    async def init_browser(self):
        """Инициализация браузера с CDP или новым профилем"""
        playwright = await async_playwright().start()
        
        # Пробуем подключиться к существующему Chrome через CDP
        try:
            self.browser = await playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
            self.context = self.browser.contexts[0]
            print("[TURBO] Подключен к Chrome через CDP на порту 9222")
        except:
            # Запускаем новый браузер с профилем аккаунта
            if self.account and self.account.profile_path:
                # Обрабатываем относительные пути типа ".profiles/dsmismirnov"
                if self.account.profile_path.startswith(".profiles"):
                    profile_path = str(Path("C:/AI/yandex") / self.account.profile_path).replace("\\", "/")
                else:
                    profile_path = str(Path(self.account.profile_path).absolute()).replace("\\", "/")
            else:
                # Если нет профиля, используем имя аккаунта
                if self.account and self.account.name:
                    profile_path = str(Path(f"C:/AI/yandex/.profiles/{self.account.name}").absolute()).replace("\\", "/")
                else:
                    profile_path = str(Path("C:/AI/yandex/.profiles/default").absolute()).replace("\\", "/")
            proxy = None
            
            if self.account and self.account.proxy:
                # Парсим прокси формата http://user:pass@ip:port
                proxy_parts = self.account.proxy.replace("http://", "").split("@")
                if len(proxy_parts) == 2:
                    auth, server = proxy_parts
                    user, password = auth.split(":")
                    proxy = {
                        "server": f"http://{server}",
                        "username": user,
                        "password": password
                    }
            
            # Убеждаемся что профиль существует
            profile_dir = Path(profile_path)
            profile_dir.mkdir(parents=True, exist_ok=True)
            print(f"[TURBO] Используем профиль: {profile_path}")
            
            self.context = await playwright.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                channel="chrome",  # Используем системный Chrome вместо Chromium
                headless=self.headless,
                proxy=proxy,
                viewport={"width": 1280, "height": 900},
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection",
                    "--start-maximized" if not self.headless else "",
                ]
            )
            self.browser = self.context.browser
            print(f"[TURBO] Запущен новый браузер с профилем {profile_path}")
    
    async def setup_tabs(self):
        """Создание мульти-табов для параллельного парсинга"""
        print(f"[TURBO] Создание {self.num_tabs} вкладок...")
        
        # Получаем существующие вкладки
        existing_pages = self.context.pages
        
        # Создаем новые если нужно
        for i in range(len(existing_pages), self.num_tabs):
            page = await self.context.new_page()
            existing_pages.append(page)
        
        # Используем нужное количество
        self.pages = existing_pages[:self.num_tabs]
        
        # КРИТИЧНО из файла 45: словарь для маппинга вкладок
        self.page_mapping = {}
        
        # Открываем Wordstat на всех вкладках
        for i, page in enumerate(self.pages):
            try:
                # ИСПРАВЛЕНИЕ из файла 45: правильная загрузка и ожидание URL
                await page.goto("https://wordstat.yandex.ru", wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_url("**/wordstat.yandex.ru/**", timeout=10000)
                
                self.page_mapping[i] = page  # Сохраняем маппинг tab_id -> page
                await asyncio.sleep(0.5)  # небольшая пауза между открытиями
                print(f"[TURBO] Tab {i}: Wordstat загружен и готов")
            except Exception as e:
                print(f"[TURBO] Tab {i}: Ошибка загрузки - {e}")
        
        # Настраиваем перехват ответов на всех вкладках
        for i, page in enumerate(self.pages):
            page.on("response", lambda response, tab_id=i: asyncio.create_task(
                self.handle_response(response, tab_id)
            ))
    
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
        """Воркер для обработки фраз на одной вкладке"""
        tab_results = []
        reload_count = 0
        
        for idx, phrase in enumerate(phrases):
            try:
                # КРИТИЧНО: Переход на Wordstat с правильным URL
                url = f"https://wordstat.yandex.ru/#!/?words={quote(phrase)}&regions=225"
                await page.goto(url, timeout=30000)
                
                # КРИТИЧНО из файла 45: полное ожидание загрузки
                await page.wait_for_url("**/wordstat.yandex.ru/**", timeout=10000)
                
                # Дополнительное ожидание из файла 45: ждём либо ответ, либо таблицу
                try:
                    # Вариант 1: ждём сетевой ответ
                    await page.wait_for_response(
                        lambda r: "wordstat.yandex.ru" in r.url and r.ok,
                        timeout=10000
                    )
                except:
                    # Вариант 2: ждём появление таблицы с результатами
                    try:
                        await page.locator("table >> tbody >> tr").first.wait_for(timeout=10000)
                    except:
                        pass  # Может не быть данных на первой загрузке
                
                # УЛУЧШЕННАЯ обработка iframe challenge из файла 45
                if await page.locator('iframe[src*="challenge"]').count() > 0:
                    print(f"[Tab {tab_id}] Обнаружен challenge в iframe для {phrase}")
                    
                    # Используем frame_locator с множественными селекторами
                    ch = page.frame_locator('iframe[src*="challenge"], iframe[name*="passp:challenge"]')
                    
                    # КРИТИЧНО из файла 45: используем get_by_label для надёжности
                    try:
                        # Пробуем найти поле по label
                        answer = ch.get_by_label('Ответ на контрольный вопрос')
                        
                        # Ждём пока поле станет доступным
                        await answer.wait_for(timeout=5000)
                        
                        # Если есть секретный ответ - вводим
                        if self.account and hasattr(self.account, 'secret_answer'):
                            await answer.fill(self.account.secret_answer)
                            
                            # Используем get_by_role для кнопки (рекомендация из файла 45)
                            submit_btn = ch.get_by_role('button', name='Продолжить')
                            await submit_btn.click()
                            
                            # Ждём возврата на Wordstat
                            await page.wait_for_url(r'.*wordstat\.yandex\.ru.*', timeout=60000)
                            print(f"[Tab {tab_id}] Challenge пройден успешно")
                        else:
                            print(f"[Tab {tab_id}] ВНИМАНИЕ: Нет секретного ответа!")
                            continue
                    except Exception as e:
                        print(f"[Tab {tab_id}] Ошибка обработки challenge: {e}")
                        continue
                
                # Проверяем не перекинуло ли на авторизацию
                if await self.auth_handler.check_auth_required(page):
                    print(f"[Tab {tab_id}] Обнаружен редирект на авторизацию, обрабатываем...")
                    
                    # Готовим данные аккаунта
                    account_data = {}
                    if self.account:
                        account_data = {
                            'login': self.account.login if hasattr(self.account, 'login') else self.account.name,
                            'password': self.account.password if hasattr(self.account, 'password') else '',
                            'secret_answer': self.account.secret_answer if hasattr(self.account, 'secret_answer') else ''
                        }
                    
                    # Запускаем автоматическую авторизацию
                    auth_success = await self.auth_handler.handle_auth_redirect(page, account_data)
                    
                    if not auth_success:
                        print(f"[Tab {tab_id}] ERROR: Не удалось авторизоваться автоматически")
                        continue
                    else:
                        print(f"[Tab {tab_id}] Авторизация успешна, продолжаем парсинг")
                        await asyncio.sleep(2)
                        # Повторяем переход на wordstat после авторизации
                        await page.goto(url, timeout=30000)
                        await page.wait_for_url("**/wordstat.yandex.ru/**", timeout=10000)
                
                # Ждем появление данных о частотности
                freq_selectors = [
                    '[data-auto="phrase-count-total"]',
                    '.b-phrase-count__total',
                    '.b-word-statistics__info-text',
                    'td.b-word-statistics__td:has-text("Показов в месяц")'
                ]
                
                frequency = None
                for selector in freq_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=5000)
                        freq_text = await page.locator(selector).first.inner_text()
                        # Парсим число из текста (убираем пробелы и запятые)
                        frequency = int(''.join(filter(str.isdigit, freq_text)))
                        if frequency > 0:
                            break
                    except:
                        continue
                
                if frequency:
                    print(f"[Tab {tab_id}] OK {phrase} = {frequency:,}")
                    tab_results.append({
                        'query': phrase,
                        'frequency': frequency,
                        'timestamp': datetime.now().isoformat()
                    })
                    self.results[phrase] = frequency
                    self.total_processed += 1
                    self.aimd.on_success()
                else:
                    print(f"[Tab {tab_id}] ERROR: Не удалось получить частотность для {phrase}")
                    self.aimd.on_error()
                
            except Exception as e:
                print(f"[Tab {tab_id}] ERROR для '{phrase}': {e}")
                reload_count += 1
                self.aimd.on_error()
                if reload_count > 3:
                    print(f"[Tab {tab_id}] Слишком много ошибок, перезагрузка...")
                    await page.reload()
                    reload_count = 0
                
            # Минимальная пауза между запросами с учетом AIMD
            await asyncio.sleep(self.aimd.get_delay())
        
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
                profile_path = acc.profile_path or f".profiles/{acc.name}"
                # Делаем полным путем если относительный
                if not profile_path.startswith("C:"):
                    profile_path = f"C:/AI/yandex/{profile_path}"
                
                all_accounts.append({
                    "name": acc.name,
                    "profile_path": profile_path,
                    "proxy": acc.proxy
                })
        
        if self.account:
            # Добавляем основной аккаунт первым
            profile_path = self.account.profile_path or f".profiles/{self.account.name}"
            if not profile_path.startswith("C:"):
                profile_path = f"C:/AI/yandex/{profile_path}"
            
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
        results = await asyncio.gather(*tasks)
        
        # Собираем все результаты
        all_results = []
        for tab_results in results:
            if tab_results:
                all_results.extend(tab_results)
        
        # Статистика
        elapsed = time.time() - self.start_time
        speed = len(all_results) / elapsed * 60 if elapsed > 0 else 0
        
        print(f"\n{'='*70}")
        print(f"   РЕЗУЛЬТАТЫ ТУРБО ПАРСИНГА")
        print(f"{'='*70}")
        print(f"  Время: {elapsed:.1f} сек")
        print(f"  Обработано: {len(all_results)}/{len(queries)}")
        print(f"  Успех: {len(all_results)/len(queries)*100:.1f}%")
        print(f"  СКОРОСТЬ: {speed:.1f} фраз/мин")
        print(f"{'='*70}")
        
        return all_results
    
    async def save_to_db(self, results: List[Dict]):
        """Сохранение результатов в БД SemTool"""
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
        """Закрытие браузера"""
        if self.browser:
            await self.browser.close()


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


# Главная функция для интеграции в SemTool
async def run_turbo_parser(queries: List[str], account: Optional[Account] = None, headless: bool = False):
    """
    Запуск турбо парсера из GUI SemTool
    
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

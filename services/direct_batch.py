# services/direct_batch.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext
from pathlib import Path
import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Константы для chunk обработки
DEFAULT_CHUNK_SIZE = 200
MAX_RETRIES = 3
RETRY_DELAY = 2

class DirectBatchProcessor:
    """Пакетная обработка прогнозов ставок Direct API"""
    
    def __init__(
        self,
        storage_state_path: str,
        proxy: Optional[str] = None,
        region_ids: Optional[List[int]] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        use_mock: bool = False
    ):
        """
        Args:
            storage_state_path: путь к файлу сессии браузера
            proxy: прокси сервер в формате http://host:port
            region_ids: список ID регионов для таргетинга
            chunk_size: размер чанка для пакетной обработки
            use_mock: использовать моковые данные вместо реального API
        """
        self.storage_state_path = storage_state_path
        self.proxy = proxy
        self.region_ids = region_ids or [213]  # По умолчанию Москва
        self.chunk_size = chunk_size
        self.use_mock = use_mock
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
    
    async def __aenter__(self):
        """Контекстный менеджер - вход"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        await self.cleanup()
    
    async def initialize(self):
        """Инициализация браузера и контекста"""
        if self.use_mock:
            logger.info("Используется mock режим")
            return
        
        try:
            p = await async_playwright().start()
            
            # Настройки браузера
            browser_args = [
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled"
            ]
            
            launch_options = {
                "headless": True,
                "args": browser_args
            }
            
            # Добавляем прокси если указан
            if self.proxy:
                launch_options["proxy"] = {"server": self.proxy}
                logger.info(f"Использование прокси: {self.proxy}")
            
            self.browser = await p.chromium.launch(**launch_options)
            
            # Создаем контекст с сохраненной сессией
            context_params = {}
            
            if Path(self.storage_state_path).exists():
                context_params["storage_state"] = self.storage_state_path
                logger.info(f"Загружена сессия из {self.storage_state_path}")
            else:
                logger.warning(f"Файл сессии не найден: {self.storage_state_path}")
            
            self.context = await self.browser.new_context(**context_params)
            
        except Exception as e:
            logger.error(f"Ошибка инициализации: {e}")
            await self.cleanup()
            raise
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    def _chunk_phrases(self, phrases: List[str]) -> List[List[str]]:
        """Разбивка фраз на чанки"""
        chunks = []
        for i in range(0, len(phrases), self.chunk_size):
            chunks.append(phrases[i:i + self.chunk_size])
        return chunks
    
    async def _get_mock_data(self, phrases: List[str]) -> List[Dict[str, Any]]:
        """Генерация моковых данных для тестирования"""
        import random
        
        results = []
        for phrase in phrases:
            results.append({
                "phrase": phrase,
                "shows": random.randint(1000, 50000),
                "clicks": random.randint(10, 1000),
                "cost": round(random.uniform(100, 5000), 2),
                "cpc": round(random.uniform(10, 200), 2),
                "ctr": round(random.uniform(0.5, 5.0), 2),
                "region_ids": self.region_ids,
                "timestamp": datetime.now().isoformat()
            })
        
        # Симуляция задержки API
        await asyncio.sleep(0.5)
        return results
    
    async def _process_chunk_with_retry(
        self,
        chunk: List[str],
        chunk_num: int,
        total_chunks: int
    ) -> List[Dict[str, Any]]:
        """Обработка чанка с повторными попытками"""
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(
                    f"Обработка чанка {chunk_num}/{total_chunks} "
                    f"({len(chunk)} фраз), попытка {attempt + 1}/{MAX_RETRIES}"
                )
                
                if self.use_mock:
                    return await self._get_mock_data(chunk)
                
                # Импортируем forecast_batch здесь чтобы избежать циклических импортов
                from .forecast_ui import forecast_batch
                
                # Вызываем forecast_batch через playwright
                results = await forecast_batch(
                    context=self.context,
                    phrases=chunk,
                    region_ids=self.region_ids
                )
                
                logger.info(f"Чанк {chunk_num} успешно обработан")
                return results
                
            except Exception as e:
                logger.error(f"Ошибка обработки чанка {chunk_num}: {e}")
                
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Повтор через {RETRY_DELAY} сек...")
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Чанк {chunk_num} не удалось обработать после {MAX_RETRIES} попыток")
                    # Возвращаем пустые результаты с ошибкой
                    return [
                        {
                            "phrase": phrase,
                            "error": str(e),
                            "timestamp": datetime.now().isoformat()
                        }
                        for phrase in chunk
                    ]
    
    async def process_phrases(
        self,
        phrases: List[str],
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Основной метод пакетной обработки фраз
        
        Args:
            phrases: список ключевых фраз для обработки
            progress_callback: коллбэк для отслеживания прогресса (progress, total)
        
        Returns:
            Список словарей с результатами прогноза
        """
        if not phrases:
            logger.warning("Пустой список фраз")
            return []
        
        logger.info(f"Начало обработки {len(phrases)} фраз")
        logger.info(f"Регионы: {self.region_ids}")
        logger.info(f"Размер чанка: {self.chunk_size}")
        
        # Разбиваем на чанки
        chunks = self._chunk_phrases(phrases)
        total_chunks = len(chunks)
        
        logger.info(f"Создано {total_chunks} чанков")
        
        all_results = []
        
        # Обрабатываем чанки последовательно
        for i, chunk in enumerate(chunks, 1):
            chunk_results = await self._process_chunk_with_retry(chunk, i, total_chunks)
            all_results.extend(chunk_results)
            
            # Вызываем коллбэк прогресса
            if progress_callback:
                progress_callback(len(all_results), len(phrases))
            
            # Небольшая пауза между чанками
            if i < total_chunks:
                await asyncio.sleep(1)
        
        logger.info(f"Обработка завершена. Получено {len(all_results)} результатов")
        return all_results
    
    def export_to_json(self, results: List[Dict[str, Any]], output_path: str):
        """Экспорт результатов в JSON"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f"Результаты экспортированы в {output_path}")
        except Exception as e:
            logger.error(f"Ошибка экспорта в JSON: {e}")
            raise
    
    def export_to_csv(self, results: List[Dict[str, Any]], output_path: str):
        """Экспорт результатов в CSV"""
        import csv
        
        try:
            if not results:
                logger.warning("Нет результатов для экспорта")
                return
            
            # Определяем поля для CSV
            fieldnames = list(results[0].keys())
            
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
            
            logger.info(f"Результаты экспортированы в {output_path}")
        except Exception as e:
            logger.error(f"Ошибка экспорта в CSV: {e}")
            raise


# Функция-обертка для обратной совместимости
async def take_bids_for_phrases(
    phrases: List[str],
    storage_state_path: str,
    proxy: str | None = None,
    region_ids: list[int] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    use_mock: bool = False,
    export_path: Optional[str] = None,
    export_format: str = 'json'
) -> List[Dict[str, Any]]:
    """
    Получить ставки/показы/клики для списка фраз через Прогноз бюджета
    
    Args:
        phrases: список ключевых фраз
        storage_state_path: путь к сохраненной сессии
        proxy: прокси сервер (опционально)
        region_ids: список ID регионов
        chunk_size: размер чанка для пакетной обработки
        use_mock: использовать моковые данные
        export_path: путь для экспорта результатов
        export_format: формат экспорта ('json' или 'csv')
    
    Returns:
        Список словарей с метриками {phrase, shows, clicks, cost, cpc, ...}
    """
    
    async with DirectBatchProcessor(
        storage_state_path=storage_state_path,
        proxy=proxy,
        region_ids=region_ids,
        chunk_size=chunk_size,
        use_mock=use_mock
    ) as processor:
        results = await processor.process_phrases(phrases)
        
        # Экспорт если указан путь
        if export_path:
            if export_format == 'csv':
                processor.export_to_csv(results, export_path)
            else:
                processor.export_to_json(results, export_path)
        
        return results


# Пример использования
if __name__ == "__main__":
    async def main():
        # Тестовые данные
        test_phrases = [
            "купить телефон москва",
            "ремонт компьютеров цена",
            "доставка еды круглосуточно"
        ]
        
        # Пример с mock данными
        results = await take_bids_for_phrases(
            phrases=test_phrases,
            storage_state_path="data/sessions/test_account.json",
            region_ids=[213, 2],  # Москва, Санкт-Петербург
            use_mock=True,
            export_path="data/output/forecast_results.json",
            export_format="json"
        )
        
        print(f"Обработано {len(results)} фраз")
        for r in results:
            print(f"{r['phrase']}: {r.get('shows', 'N/A')} показов, {r.get('clicks', 'N/A')} кликов")
    
    asyncio.run(main())

"""
Full Pipeline Worker для Turbo Parser
Wordstat → Direct → Clustering → Export
"""

import asyncio
import time
import traceback
from datetime import datetime

from PySide6.QtCore import QThread, Signal


class FullPipelineWorkerThread(QThread):
    """Поток для FULL PIPELINE: Wordstat → Direct → Clustering"""
    log_signal = Signal(str, str, str, str, str, str, str, str)  # время, фраза, частота, CPC, показы, бюджет, группа, статус
    stats_signal = Signal(int, int, int, float, float)  # обработано, успешно, ошибок, скорость, время
    log_message = Signal(str)
    error_signal = Signal(str)
    progress_signal = Signal(int, int, str)  # текущий, всего, этап
    finished_signal = Signal(bool, str)
    results_ready = Signal(list)  # Полные результаты для таблицы
    
    def __init__(self, queries, region=225):
        super().__init__()
        self.queries = queries
        self.region = region
        self.start_time = None
        self._cancelled = False
        
    def run(self):
        """Запуск FULL PIPELINE"""
        self.log_message.emit(f"🚀 Запуск Full Pipeline: {len(self.queries)} фраз")
        self.start_time = time.time()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = False
        message = ""
        
        try:
            results = loop.run_until_complete(self._run_full_pipeline())
            message = f"✅ Обработано {len(results)} фраз"
            success = True
            self.results_ready.emit(results)
        except Exception as exc:
            message = f"❌ Ошибка: {exc}"
            self.log_message.emit(traceback.format_exc())
            self.error_signal.emit(str(exc))
        finally:
            duration = time.time() - self.start_time if self.start_time else 0
            self.log_message.emit(f"⏱ Время выполнения: {duration:.1f} сек")
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except:
                pass
            loop.close()
            self.finished_signal.emit(success, message)
    
    async def _run_full_pipeline(self):
        """Полный pipeline: freq → budget → cluster"""
        from ..services.frequency import parse_batch_wordstat
        from ..services.direct import forecast_batch_direct, merge_freq_and_forecast
        
        total_steps = len(self.queries)
        results = []
        
        # ШАГ 1: Парсинг частотности (Wordstat)
        self.log_message.emit("📊 Этап 1/3: Парсинг частотности (Wordstat)...")
        self.progress_signal.emit(0, total_steps, "Wordstat")
        
        freq_results = await parse_batch_wordstat(
            self.queries,
            chunk_size=80,
            region=self.region
        )
        
        for i, result in enumerate(freq_results):
            if self._cancelled:
                break
            phrase = result['phrase']
            freq = result['freq']
            self.log_signal.emit(
                datetime.now().strftime("%H:%M:%S"),
                phrase,
                f"{freq:,}",
                "-", "-", "-", "-", "📊"
            )
            self.progress_signal.emit(i + 1, total_steps, "Wordstat")
            await asyncio.sleep(0.01)  # UI update
        
        if self._cancelled:
            return []
        
        # ШАГ 2: Прогноз бюджета (Direct)
        self.log_message.emit("💰 Этап 2/3: Прогноз бюджета (Direct)...")
        self.progress_signal.emit(0, len(freq_results), "Direct")
        
        forecast_results = await forecast_batch_direct(
            freq_results,
            chunk_size=100,
            region=self.region
        )
        
        # ШАГ 3: Объединение данных
        self.log_message.emit("🔗 Этап 3/3: Объединение и группировка...")
        merged = await merge_freq_and_forecast(freq_results, forecast_results)
        
        # ШАГ 4: Кластеризация
        clustered = await self._cluster_phrases(merged)
        
        # Финальный лог с полными данными
        for i, result in enumerate(clustered):
            phrase = result.get('phrase', '')
            freq = result.get('freq', 0)
            cpc = result.get('cpc', 0)
            impressions = result.get('impressions', 0)
            budget = result.get('budget', 0)
            stem = result.get('stem', '')
            
            self.log_signal.emit(
                datetime.now().strftime("%H:%M:%S"),
                phrase,
                f"{freq:,}",
                f"{cpc:.2f}",
                f"{impressions:,}",
                f"{budget:.2f}",
                stem[:20],  # First 20 chars
                "✅"
            )
            self.progress_signal.emit(i + 1, len(clustered), "Готово")
        
        # Статистика
        elapsed = time.time() - self.start_time
        speed = len(clustered) / elapsed * 60 if elapsed > 0 else 0
        self.stats_signal.emit(len(clustered), len(clustered), 0, speed, elapsed)
        
        return clustered
    
    async def _cluster_phrases(self, data: list) -> list:
        """Кластеризация по стеммам (NLTK)"""
        try:
            from nltk.stem.snowball import SnowballStemmer
            from nltk.corpus import stopwords
            import nltk
            
            # Скачиваем данные если нужно
            try:
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('stopwords', quiet=True)
            
            stemmer = SnowballStemmer('russian')
            russian_stopwords = set(stopwords.words('russian'))
            
            grouped = {}
            for item in data:
                phrase = item['phrase'].lower()
                words = phrase.split()
                
                # Фильтруем стоп-слова
                filtered = [w for w in words if w not in russian_stopwords]
                if not filtered:
                    filtered = words  # Если все стоп-слова, берем оригинал
                
                # Стемминг первого значимого слова
                stem = stemmer.stem(filtered[0]) if filtered else phrase
                
                if stem not in grouped:
                    grouped[stem] = []
                
                item['stem'] = stem
                grouped[stem].append(item)
            
            # Добавляем статистику по группам
            result = []
            for stem, items in grouped.items():
                avg_freq = sum(i.get('freq', 0) for i in items) / len(items)
                total_budget = sum(i.get('budget', 0) for i in items)
                
                for item in items:
                    item['group_size'] = len(items)
                    item['group_avg_freq'] = avg_freq
                    item['group_total_budget'] = total_budget
                    result.append(item)
            
            # Сортируем по частотности
            result.sort(key=lambda x: x.get('freq', 0), reverse=True)
            
            return result
            
        except Exception as e:
            self.log_message.emit(f"⚠ Кластеризация недоступна: {e}")
            # Возвращаем без кластеризации
            for item in data:
                item['stem'] = '-'
                item['group_size'] = 1
            return data
    
    def cancel(self):
        """Отмена выполнения"""
        self._cancelled = True

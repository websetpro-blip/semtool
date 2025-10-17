"""
Full Pipeline Worker — автоматизация всего конвейера под ключ
WS → Direct → Clustering → Minus → Export, поддержка задачного файла сцен
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from PySide6.QtCore import QThread, Signal

# Внутренние сервисы
# Сервисы вызываются как обычные python-функции/корутины, ожидаемые точки входа:
# - frequency.run_frequency_batch(queries: List[str], region: int, out_dir: Path) -> Path
# - direct_batch.run_direct_batch(input_path: Path, out_dir: Path) -> Path
# - clustering.run_clustering(input_path: Path, out_dir: Path) -> Path
# - minus_words.run_minus_words(input_path: Path, out_dir: Path) -> Path
# - export.run_export(input_path: Path, out_dir: Path) -> Path
# Если у модуля отличающиеся имена функций — адаптируйте в ServiceAdapter ниже.

try:
    from services import frequency as frequency_service
except Exception:  # логируем, но продолжаем — возможно вызов через CLI-обертки
    frequency_service = None

try:
    from services import direct_batch as direct_service
except Exception:
    direct_service = None

# Кластеризация может лежать в core/services/utils — пробуем несколько импортов
clustering_service = None
for mod_path in (
    "services.clustering",
    "core.clustering",
    "utils.clustering",
    "services.cluster",
    "core.cluster",
):
    if clustering_service is None:
        try:
            clustering_service = __import__(mod_path, fromlist=["*"])
        except Exception:
            pass

try:
    from services import minus_words as minus_service
except Exception:
    minus_service = None

# Экспорт результатов (если присутствует)
export_service = None
for mod_path in (
    "services.export",
    "core.export",
    "utils.export",
    "services.exporter",
):
    if export_service is None:
        try:
            export_service = __import__(mod_path, fromlist=["*"])
        except Exception:
            pass


@dataclass
class StageResult:
    name: str
    input_path: Optional[Path]
    output_path: Optional[Path]
    ok: bool
    meta: Dict[str, Any]


class ServiceAdapter:
    """Адаптер для вызова разных реализаций сервисов единым способом."""

    @staticmethod
    async def run_frequency(queries: List[str], region: int, out_dir: Path) -> Path:
        # Попытка 1: нативная функция
        if frequency_service and hasattr(frequency_service, "run_frequency_batch"):
            return await _maybe_await(
                frequency_service.run_frequency_batch(queries=queries, region=region, out_dir=out_dir)
            )
        # Попытка 2: возможная sync-функция
        if frequency_service and hasattr(frequency_service, "run"):
            return await _maybe_await(
                frequency_service.run(queries=queries, region=region, out_dir=out_dir)
            )
        # Попытка 3: CLI
        return await _run_cli([
            sys.executable,
            "-m",
            "services.frequency",
            "--region",
            str(region),
            "--out",
            str(out_dir),
            "--queries",
            json.dumps(queries, ensure_ascii=False),
        ])

    @staticmethod
    async def run_direct(input_path: Path, out_dir: Path) -> Path:
        if direct_service and hasattr(direct_service, "run_direct_batch"):
            return await _maybe_await(
                direct_service.run_direct_batch(input_path=input_path, out_dir=out_dir)
            )
        if direct_service and hasattr(direct_service, "run"):
            return await _maybe_await(
                direct_service.run(input_path=input_path, out_dir=out_dir)
            )
        return await _run_cli([
            sys.executable,
            "-m",
            "services.direct_batch",
            "--in",
            str(input_path),
            "--out",
            str(out_dir),
        ])

    @staticmethod
    async def run_clustering(input_path: Path, out_dir: Path) -> Path:
        if clustering_service:
            for fn in ("run_clustering", "run", "cluster_batch"):
                if hasattr(clustering_service, fn):
                    return await _maybe_await(
                        getattr(clustering_service, fn)(input_path=input_path, out_dir=out_dir)
                    )
        return await _run_cli([
            sys.executable,
            "-m",
            "services.clustering",
            "--in",
            str(input_path),
            "--out",
            str(out_dir),
        ])

    @staticmethod
    async def run_minus(input_path: Path, out_dir: Path) -> Path:
        if minus_service and hasattr(minus_service, "run_minus_words"):
            return await _maybe_await(
                minus_service.run_minus_words(input_path=input_path, out_dir=out_dir)
            )
        if minus_service and hasattr(minus_service, "run"):
            return await _maybe_await(
                minus_service.run(input_path=input_path, out_dir=out_dir)
            )
        return await _run_cli([
            sys.executable,
            "-m",
            "services.minus_words",
            "--in",
            str(input_path),
            "--out",
            str(out_dir),
        ])

    @staticmethod
    async def run_export(input_path: Path, out_dir: Path) -> Path:
        if export_service:
            for fn in ("run_export", "run", "export_batch"):
                if hasattr(export_service, fn):
                    return await _maybe_await(
                        getattr(export_service, fn)(input_path=input_path, out_dir=out_dir)
                    )
        # CLI fallback
        return await _run_cli([
            sys.executable,
            "-m",
            "services.export",
            "--in",
            str(input_path),
            "--out",
            str(out_dir),
        ])


async def _maybe_await(result):
    if asyncio.iscoroutine(result):
        return await result
    return result


async def _run_cli(cmd: List[str]) -> Path:
    """Запускает подпроцесс, ожидает завершения, валидирует выходной путь из stdout."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(Path.cwd()),
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{stderr.decode(errors='ignore')}")
    # Ожидаем, что процесс выведет путь результата одной строкой JSON: {"output": "/path"}
    try:
        data = json.loads(stdout.decode(errors="ignore"))
        out = Path(data.get("output"))
        if not out.exists():
            raise FileNotFoundError(out)
        return out
    except Exception as e:
        raise RuntimeError(f"Invalid CLI output for {' '.join(cmd)}: {e}\nSTDOUT: {stdout[:500].decode(errors='ignore')}")


class FullPipelineWorkerThread(QThread):
    """Поток для полного конвейера: WS → Direct → Clustering → Minus → Export."""

    # время, фраза, частота, CPC, показы, бюджет, группа, статус
    log_signal = Signal(str, str, str, str, str, str, str, str)
    # обработано, успешно, ошибок, скорость, время
    stats_signal = Signal(int, int, int, float, float)
    # общий лог одной строкой
    log_message = Signal(str)
    error_signal = Signal(str)
    # текущий, всего, этап
    progress_signal = Signal(int, int, str)
    finished_signal = Signal(bool, str)
    # Полные результаты (список файлов/объектов) для таблицы/интерфейса
    results_ready = Signal(list)

    def __init__(self, queries: Optional[List[str]] = None, region: int = 225,
                 task_file: Optional[str] = None, out_root: Optional[str] = None):
        super().__init__()
        self.queries = queries or []
        self.region = region
        self.task_file = task_file
        self.out_root = Path(out_root) if out_root else Path("runtime/outputs")
        self._cancelled = False
        self.start_time: Optional[float] = None

    # Публичные API
    def cancel(self):
        self._cancelled = True

    # Основной цикл
    def run(self):
        self.log_message.emit(f"🚀 Запуск Full Pipeline, время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.start_time = time.time()
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(self._run_pipeline())
            self.results_ready.emit([str(p) for p in results if p])
            self.finished_signal.emit(True, "Готово")
        except Exception:
            err = traceback.format_exc()
            self.error_signal.emit(err)
            self.finished_signal.emit(False, "Ошибка выполнения, детали в логе")
        finally:
            try:
                loop.close()
            except Exception:
                pass

    async def _run_pipeline(self) -> List[Path]:
        # Поддержка задачного файла: multiple scenes
        if self.task_file:
            return await self._run_from_task_file(Path(self.task_file))
        # Иначе — одиночный прогон по self.queries
        return await self._run_single_scene(self.queries, scene_name="ad-hoc")

    async def _run_from_task_file(self, path: Path) -> List[Path]:
        if not path.exists():
            raise FileNotFoundError(f"Task file not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        scenes: List[Dict[str, Any]] = data.get("scenes") or []
        results: List[Path] = []
        self.log_message.emit(f"🔧 Загружено сцен: {len(scenes)} из {path}")
        for idx, scene in enumerate(scenes, start=1):
            if self._cancelled:
                self.log_message.emit("⛔ Прервано пользователем")
                break
            queries = scene.get("queries") or []
            region = int(scene.get("region") or self.region)
            name = scene.get("name") or f"scene_{idx:02d}"
            self.log_message.emit(f"▶️ Сцена {idx}/{len(scenes)}: {name}, фраз: {len(queries)}, регион: {region}")
            out_files = await self._run_single_scene(queries, region=region, scene_name=name)
            results.extend(out_files)
        return results

    async def _run_single_scene(self, queries: List[str], region: Optional[int] = None, scene_name: str = "scene") -> List[Path]:
        region = int(region or self.region)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_out = self.out_root / f"{scene_name}_{ts}"
        ws_out = base_out / "ws"
        dr_out = base_out / "direct"
        cl_out = base_out / "cluster"
        mn_out = base_out / "minus"
        ex_out = base_out / "export"
        for d in (ws_out, dr_out, cl_out, mn_out, ex_out):
            d.mkdir(parents=True, exist_ok=True)

        outputs: List[Path] = []

        # 1) Wordstat / Frequency
        self._progress(1, 5, f"Wordstat/Frequency: {len(queries)} фраз, регион {region}")
        ws_path: Path = await ServiceAdapter.run_frequency(queries=queries, region=region, out_dir=ws_out)
        self.log_message.emit(f"✅ Frequency готово: {ws_path}")
        outputs.append(ws_path)

        # 2) Direct Batch
        self._progress(2, 5, "Direct Batch: генерация кампаний/групп")
        dr_path: Path = await ServiceAdapter.run_direct(input_path=ws_path, out_dir=dr_out)
        self.log_message.emit(f"✅ Direct готово: {dr_path}")
        outputs.append(dr_path)

        # 3) Clustering
        self._progress(3, 5, "Clustering: группировка и семантика")
        cl_path: Path = await ServiceAdapter.run_clustering(input_path=dr_path, out_dir=cl_out)
        self.log_message.emit(f"✅ Clustering готово: {cl_path}")
        outputs.append(cl_path)

        # 4) Minus-слова
        self._progress(4, 5, "Минусовка: вычисление минус-слов")
        mn_path: Path = await ServiceAdapter.run_minus(input_path=cl_path, out_dir=mn_out)
        self.log_message.emit(f"✅ Минусовка готово: {mn_path}")
        outputs.append(mn_path)

        # 5) Export
        self._progress(5, 5, "Экспорт результатов")
        ex_path: Path = await ServiceAdapter.run_export(input_path=mn_path, out_dir=ex_out)
        self.log_message.emit(f"✅ Экспорт готово: {ex_path}")
        outputs.append(ex_path)

        return outputs

    def _progress(self, cur: int, total: int, stage: str):
        if self.start_time:
            elapsed = time.time() - self.start_time
            speed = cur / max(elapsed, 1e-6)
            self.stats_signal.emit(cur, cur, 0, speed, elapsed)
        self.progress_signal.emit(cur, total, stage)
        self.log_message.emit(f"➡️ {stage}")


# Утилита CLI для автономного запуска этого воркера (без GUI)
# Пример задачного файла (tasks.json):
# {
#   "scenes": [
#     {"name": "niche_1", "region": 213, "queries": ["купить пылесос", "пылесос dyson"]},
#     {"name": "niche_2", "queries": ["робот пылесос", "wet&dry vacuum"]}
#   ]
# }
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Full pipeline worker runner")
    parser.add_argument("--tasks", dest="tasks", type=str, help="Путь к задачному файлу JSON", default=None)
    parser.add_argument("--queries", dest="queries", type=str, help="JSON-массив фраз для ad-hoc запуска", default=None)
    parser.add_argument("--region", dest="region", type=int, default=225)
    parser.add_argument("--out", dest="out", type=str, default="runtime/outputs")

    args = parser.parse_args()

    queries: List[str] = []
    task_file: Optional[str] = args.tasks
    if args.queries:
        try:
            queries = json.loads(args.queries)
        except Exception:
            print("[ERR] --queries должен быть JSON-массивом строк", file=sys.stderr)
            sys.exit(2)

    # Без GUI-сигналов: просто запустить и напечатать финальные пути
    worker = FullPipelineWorkerThread(
        queries=queries,
        region=args.region,
        task_file=task_file,
        out_root=args.out,
    )

    # Простейшие

# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import re

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..dialogs.geo_dialog import GeoDialog
from ..widgets.toolbar import MainToolbar
from ..keys_panel import KeysPanel
from ...services.accounts import get_profile_ctx, list_profiles
from ...services.analytics import enrich_metrics
from ...services.exporter import export_csv
from ...services.minus_words import MinusWordsExtractor
from ...services.wordstat_bridge import (
    collect_depth,
    collect_frequency,
    collect_forecast,
)


COLUMNS = [
    "Фраза",
    "WS",
    '"WS"',
    "!WS",
    "Показы",
    "Клики",
    "CTR",
    "CPC",
    "Спис. цена",
    "Стоимость",
    "CPA",
    "Конв.%",
    "Группа",
    "Статус",
]


class ParsingWorker(QThread):
    """Асинхронные вызовы сервисных функций для парсинга."""

    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, mode: str, phrases: list[str], params: dict) -> None:
        super().__init__()
        self._mode = mode
        self._phrases = phrases
        self._params = params

    def run(self) -> None:  # type: ignore[override]
        try:
            if self._mode == "freq":
                rows = collect_frequency(
                    self._phrases,
                    modes=self._params.get("modes", {}),
                    regions=self._params.get("regions") or [225],
                    profile=self._params.get("profile"),
                )
            elif self._mode in {"depth-left", "depth-right"}:
                rows = collect_depth(
                    self._phrases,
                    column="left" if self._mode.endswith("left") else "right",
                    pages=self._params.get("pages", 1),
                    regions=self._params.get("regions") or [225],
                    profile=self._params.get("profile"),
                )
            elif self._mode == "forecast":
                rows = collect_forecast(
                    self._phrases,
                    regions=self._params.get("regions") or [225],
                    profile_ctx=self._params.get("ctx") or {},
                )
            else:
                rows = []
            self.finished.emit(rows)
        except Exception as exc:  # pragma: no cover
            self.failed.emit(str(exc))


class ParsingTab(QWidget):
    """Вкладка «Парсинг»: частотка, глубина, прогноз, аналитика."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._regions = [225]
        self._profile: str | None = None
        self._worker: ParsingWorker | None = None
        self._minus_extractor = MinusWordsExtractor()

        self.toolbar = MainToolbar(self)
        self.toolbar.sig.open_geo.connect(self._choose_geo)
        self.toolbar.sig.profile_changed.connect(self._set_profile)
        self.toolbar.sig.run_freq.connect(lambda: self._run("freq"))
        self.toolbar.sig.run_depth_left.connect(lambda: self._run("depth-left"))
        self.toolbar.sig.run_depth_right.connect(lambda: self._run("depth-right"))
        self.toolbar.sig.run_forecast.connect(lambda: self._run("forecast"))
        self.toolbar.sig.run_minus.connect(self._run_minus)
        self.toolbar.sig.run_stopwords.connect(self._export_stopwords)
        self.toolbar.sig.run_export.connect(self._export_csv)
        self.toolbar.sig.open_analytics.connect(self._run_analytics)

        self._phrases_edit = QTextEdit(placeholderText="Введите фразы (по одной на строку)…")
        self._phrases_edit.setAcceptRichText(False)

        self._table = QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)

        self._keys_panel = KeysPanel(self)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._phrases_edit)
        splitter.addWidget(self._table)
        splitter.addWidget(self._keys_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 2)
        splitter.setChildrenCollapsible(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self.toolbar)
        layout.addWidget(splitter, 1)

        self._refresh_profiles()

    # ------------------------------------------------------------------ helpers
    def _phrases(self) -> list[str]:
        return [line.strip() for line in self._phrases_edit.toPlainText().splitlines() if line.strip()]

    def _ensure_idle(self) -> bool:
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "Задача выполняется", "Дождитесь завершения текущего запроса.")
            return False
        return True

    def _refresh_profiles(self) -> None:
        profiles = list_profiles()
        self.toolbar.set_profiles(profiles)
        self._profile = profiles[0] if profiles else None

    def _append_rows(self, rows: list[dict], mode: str) -> None:
        if not rows:
            return
        for payload in rows:
            row_index = self._table.rowCount()
            self._table.insertRow(row_index)
            mapping = {
                "phrase": payload.get("phrase", ""),
                "ws": payload.get("ws", payload.get("freq_total", "")),
                "qws": payload.get("qws", payload.get("freq_quotes", "")),
                "bws": payload.get("bws", payload.get("freq_exact", "")),
                "shows": payload.get("shows", ""),
                "clicks": payload.get("clicks", ""),
                "ctr": payload.get("ctr", ""),
                "cpc": payload.get("cpc", ""),
                "avg_bid": payload.get("avg_bid", ""),
                "cost": payload.get("cost", ""),
                "cpa": payload.get("cpa", ""),
                "cr": payload.get("cr", ""),
                "group": payload.get("group", ""),
                "status": payload.get("status", "OK" if mode != "forecast" else "Forecast"),
            }
            for column, key in enumerate([
                "phrase",
                "ws",
                "qws",
                "bws",
                "shows",
                "clicks",
                "ctr",
                "cpc",
                "avg_bid",
                "cost",
                "cpa",
                "cr",
                "group",
                "status",
            ]):
                item = QTableWidgetItem(str(mapping.get(key, "")))
                if column in (1, 2, 3, 4, 5, 7, 8, 9, 10, 11):
                    item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(row_index, column, item)

        grouped: dict[str, list[dict]] = {}
        for idx in range(self._table.rowCount()):
            phrase_item = self._table.item(idx, 0)
            freq_item = self._table.item(idx, 1)
            phrase = phrase_item.text() if phrase_item else ""
            group_name = (self._table.item(idx, 12).text() if self._table.item(idx, 12) else "") or "Без группы"
            grouped.setdefault(group_name, []).append(
                {
                    "phrase": phrase,
                    "freq_total": self._int_value(freq_item),
                    "freq_quotes": self._int_cell(idx, 2),
                    "freq_exact": self._int_cell(idx, 3),
                }
            )
        self._keys_panel.load_groups(grouped)

    def _cell_text(self, row: int, col: int) -> str:
        item = self._table.item(row, col)
        return item.text() if item else ""

    def _int_cell(self, row: int, col: int) -> int:
        return self._int_value(self._table.item(row, col))

    @staticmethod
    def _int_value(item: QTableWidgetItem | None) -> int:
        if not item:
            return 0
        try:
            return int(item.text().replace(" ", ""))
        except ValueError:
            return 0

    def _tokenize(self, phrase: str) -> list[str]:
        return [w for w in re.findall(r"\b[а-яёa-z0-9]+\b", phrase.lower()) if len(w) > 2]

    # ----------------------------------------------------------------- handlers
    def _run(self, mode: str) -> None:
        if not self._ensure_idle():
            return
        phrases = self._phrases()
        if not phrases:
            QMessageBox.warning(self, "Нет данных", "Добавьте фразы в левую панель перед запуском.")
            return

        params = {"regions": self._regions, "profile": self._profile}
        if mode == "freq":
            params["modes"] = {"ws": True, "qws": True, "bws": True}
        elif mode in {"depth-left", "depth-right"}:
            params["pages"] = 3
        elif mode == "forecast":
            params["ctx"] = get_profile_ctx(self._profile)

        self._table.setRowCount(0)
        self._worker = ParsingWorker(mode, phrases, params)
        self._worker.finished.connect(lambda rows: self._handle_result(rows, mode))
        self._worker.failed.connect(self._handle_error)
        self._worker.start()

    def _handle_result(self, rows: list[dict], mode: str) -> None:
        self._worker = None
        self._append_rows(rows, mode)

    def _handle_error(self, message: str) -> None:
        self._worker = None
        QMessageBox.critical(self, "Ошибка", message)

    def _choose_geo(self) -> None:
        dialog = GeoDialog(parent=self)
        dialog.exec()
        self._regions = dialog.selected_region_ids()

    def _set_profile(self, name: str) -> None:
        self._profile = name or None

    def _run_minus(self) -> None:
        if self._table.rowCount() == 0:
            QMessageBox.information(self, "Нет данных", "Сначала получите частотность или прогноз.")
            return

        results: dict[str, list[str]] = {}
        grouped: dict[str, list[dict]] = {}

        for row in range(self._table.rowCount()):
            group_name = self._cell_text(row, 12) or "Без группы"
            grouped.setdefault(group_name, []).append(
                {
                    "phrase": self._cell_text(row, 0),
                    "freq_total": self._int_cell(row, 1),
                    "freq_quotes": self._int_cell(row, 2),
                    "freq_exact": self._int_cell(row, 3),
                }
            )

        for group_name, phrases in grouped.items():
            minus = self._minus_extractor.extract_from_group(phrases)
            if minus:
                results[group_name] = minus

        if not results:
            QMessageBox.information(self, "Минус-слова", "Не удалось подобрать минуса по текущим данным.")
            return

        text_lines = []
        for group_name, words in results.items():
            text_lines.append(f"[{group_name}]")
            text_lines.extend(f"-{word}" for word in words)
            text_lines.append("")

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить минус-слова",
            "minus_words.txt",
            "Text files (*.txt)",
        )
        if filename:
            Path(filename).write_text("\n".join(text_lines).strip(), encoding="utf-8")
            QMessageBox.information(self, "Минус-слова", f"Минус-слова сохранены в {filename}.")
        else:
            QMessageBox.information(self, "Минус-слова", "\n".join(text_lines))

    def _export_stopwords(self) -> None:
        if self._table.rowCount() == 0:
            QMessageBox.information(self, "Нет данных", "Сначала получите частотность или прогноз.")
            return

        tokens: set[str] = set()
        for row in range(self._table.rowCount()):
            phrase = self._cell_text(row, 0)
            tokens.update(self._tokenize(phrase))

        if not tokens:
            QMessageBox.information(self, "Стоп-слова", "Нечего экспортировать.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить стоп-слова",
            "stop_words.txt",
            "Text files (*.txt)",
        )
        if not filename:
            return

        Path(filename).write_text("\n".join(sorted(tokens)), encoding="utf-8")
        QMessageBox.information(self, "Стоп-слова", f"Список сохранён в {filename}.")

    def _run_analytics(self) -> None:
        if self._table.rowCount() == 0:
            QMessageBox.information(self, "Аналитика", "Таблица пуста. Добавьте данные перед расчётом.")
            return
        enrich_metrics(self._table)
        QMessageBox.information(self, "Аналитика", "Метрики обновлены в таблице.")

    def _export_csv(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт в CSV",
            "keyset_export.csv",
            "CSV Files (*.csv)",
        )
        if not filename:
            return
        export_csv(self._table, filename)

    # ----------------------------------------------------------- external hooks
    def append_phrases(self, phrases: list[str]) -> None:
        existing = self._phrases_edit.toPlainText().splitlines()
        merged = existing + [phrase for phrase in phrases if phrase.strip()]
        self._phrases_edit.setPlainText("\n".join(line.strip() for line in merged if line.strip()))

    def refresh_profiles(self) -> None:
        self._refresh_profiles()


__all__ = ["ParsingTab"]

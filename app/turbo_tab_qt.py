"""
ТУРБО ПАРСЕР TAB - GUI вкладка для турбо парсинга (PySide6)
Интерфейс как в DirectParser с таблицей логов
"""

import asyncio
import time
import traceback
from pathlib import Path
from datetime import datetime
import json
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
    QCheckBox, QSpinBox, QComboBox, QFileDialog, QMessageBox,
    QHeaderView, QRadioButton, QButtonGroup, QLineEdit,
    QPlainTextEdit
)

from ..services import accounts as account_service
from ..workers.turbo_parser_integration import TurboWordstatParser


class ParserWorkerThread(QThread):
    """Поток для выполнения парсинга"""
    log_signal = Signal(str, str, str, str, str, str)  # время, аккаунт, фраза, частота, статус, скорость
    stats_signal = Signal(int, int, int, float, float)  # обработано, успешно, ошибок, скорость, время\r\n    log_message = Signal(str)  # Короткие уведомления в UI\r\n    error_signal = Signal(str)  # Текст ошибки для отображения\r\n    finished_signal = Signal(bool, str)  # успех, сообщение\r\n    
    def __init__(self, queries, account, headless, mode, visual_mode=True, num_browsers=3):
        super().__init__()
        self.queries = queries
        self.account = account
        self.headless = headless
        self.mode = mode
        self.visual_mode = visual_mode
        self.num_browsers = num_browsers
        self.parser = None
        self.start_time = None
        
    def run(self):
        """Запуск парсинга в отдельном потоке"""
        self.log_message.emit(f"Старт парсинга: {len(self.queries)} фраз")
        self.start_time = time.time()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = False
        message = ""
        try:
            results = loop.run_until_complete(self._run_async())
            message = f"Обработано {len(results)} фраз"
            success = True
        except Exception as exc:
            message = str(exc)
            self.log_message.emit(f"Ошибка: {exc}")
            self.log_message.emit(traceback.format_exc())
            self.error_signal.emit(str(exc))
        finally:
            duration = 0.0
            if self.start_time:
                duration = time.time() - self.start_time
            self.log_message.emit(f"Время выполнения: {duration:.1f} с")
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()
            self.finished_signal.emit(success, message or "Парсинг завершён")
    
    async def _run_async(self):
        """Асинхронный запуск парсера"""
        self.parser = TurboWordstatParser(
            account=self.account, 
            headless=self.headless,
            visual_mode=self.visual_mode
        )
        
        # Настраиваем количество браузеров для визуального режима
        if self.visual_mode:
            self.parser.num_browsers = self.num_browsers
        
        # Настраиваем режим
        if self.mode == "turbo":
            self.parser.num_tabs = 10
        elif self.mode == "fast":
            self.parser.num_tabs = 5
        else:
            self.parser.num_tabs = 1
        
        try:
            results = await self.parser.parse_batch(self.queries)

            elapsed = max(time.time() - (self.start_time or time.time()), 1e-6)
            processed = len(results)
            errors = 0
            if isinstance(results, list):
                errors = sum(1 for item in results if isinstance(item, dict) and item.get("error"))
            success_count = processed - errors
            speed_per_min = processed / elapsed * 60 if elapsed > 0 else 0

            for result in results:
                query = result.get("query", "") if isinstance(result, dict) else str(result)
                freq_value = 0
                if isinstance(result, dict):
                    freq_value = result.get("frequency") or 0
                formatted_freq = (
                    f"{int(freq_value):,}" if isinstance(freq_value, (int, float)) else str(freq_value)
                )
                status = result.get("status", "✓") if isinstance(result, dict) else "✓"
                self.log_signal.emit(
                    datetime.now().strftime("%H:%M:%S"),
                    self.account.name if self.account else "default",
                    query,
                    formatted_freq,
                    status,
                    f"{speed_per_min:.1f}"
                )

            self.stats_signal.emit(processed, success_count, errors, speed_per_min, elapsed)
            self.log_message.emit("Парсинг завершён.")
            return results

        finally:
            if self.parser:
                await self.parser.close()


class TurboParserTab(QWidget):
    """Вкладка турбо парсера с интерфейсом как в DirectParser"""
    
    def __init__(self):
        super().__init__()
        self.worker_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        """Создание интерфейса вкладки"""
        layout = QVBoxLayout(self)
        
        # Верхняя панель управления
        control_group = QGroupBox("Управление парсингом")
        control_layout = QVBoxLayout()
        
        # Строка 1: Выбор аккаунтов
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Аккаунт:"))
        
        self.account_combo = QComboBox()
        self.account_combo.setMinimumWidth(200)
        row1.addWidget(self.account_combo)
        
        self.refresh_accounts_btn = QPushButton("Обновить")
        self.refresh_accounts_btn.clicked.connect(self.load_accounts)
        row1.addWidget(self.refresh_accounts_btn)
        
        self.auto_login_btn = QPushButton("Автологин")
        self.auto_login_btn.clicked.connect(self.auto_login)
        row1.addWidget(self.auto_login_btn)
        
        row1.addStretch()
        control_layout.addLayout(row1)
        
        # Строка 2: Настройки парсинга
        row2 = QHBoxLayout()
        
        row2.addWidget(QLabel("Режим:"))
        self.mode_group = QButtonGroup()
        
        self.turbo_radio = QRadioButton("Турбо (195 фраз/мин)")
        self.turbo_radio.setChecked(True)
        self.mode_group.addButton(self.turbo_radio, 0)
        row2.addWidget(self.turbo_radio)
        
        self.fast_radio = QRadioButton("Быстрый (100 фраз/мин)")
        self.mode_group.addButton(self.fast_radio, 1)
        row2.addWidget(self.fast_radio)
        
        self.normal_radio = QRadioButton("Обычный (20 фраз/мин)")
        self.mode_group.addButton(self.normal_radio, 2)
        row2.addWidget(self.normal_radio)
        
        row2.addWidget(QLabel("Регион:"))
        self.region_edit = QLineEdit("225")
        self.region_edit.setMaximumWidth(60)
        row2.addWidget(self.region_edit)
        
        self.headless_check = QCheckBox("Фоновый режим")
        self.headless_check.setChecked(False)  # По умолчанию визуальный режим
        self.headless_check.toggled.connect(self.on_headless_toggled)
        row2.addWidget(self.headless_check)
        
        self.visual_check = QCheckBox("Визуальный режим (несколько браузеров)")
        self.visual_check.setChecked(True)  # По умолчанию включен
        self.visual_check.toggled.connect(self.on_visual_toggled)
        row2.addWidget(self.visual_check)
        
        # Настройка количества браузеров
        row2.addWidget(QLabel("Браузеров:"))
        self.num_browsers_spin = QSpinBox()
        self.num_browsers_spin.setMinimum(1)
        self.num_browsers_spin.setMaximum(6)
        self.num_browsers_spin.setValue(3)
        self.num_browsers_spin.setMaximumWidth(50)
        row2.addWidget(self.num_browsers_spin)
        
        row2.addStretch()
        control_layout.addLayout(row2)
        
        # Строка 3: Загрузка фраз
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Фразы:"))
        
        self.load_phrases_btn = QPushButton("Загрузить из файла")
        self.load_phrases_btn.clicked.connect(self.load_phrases)
        row3.addWidget(self.load_phrases_btn)
        
        self.clear_phrases_btn = QPushButton("Очистить")
        self.clear_phrases_btn.clicked.connect(self.clear_phrases)
        row3.addWidget(self.clear_phrases_btn)
        
        self.phrases_count_label = QLabel("0 фраз загружено")
        row3.addWidget(self.phrases_count_label)
        
        row3.addStretch()
        control_layout.addLayout(row3)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Текстовое поле для фраз
        phrases_group = QGroupBox("Фразы для парсинга")
        phrases_layout = QVBoxLayout()
        
        self.phrases_text = QPlainTextEdit()
        self.phrases_text.setMaximumHeight(150)
        phrases_layout.addWidget(self.phrases_text)
        
        phrases_group.setLayout(phrases_layout)
        layout.addWidget(phrases_group)
        
        # Панель логов (как в DirectParser)
        logs_group = QGroupBox("Лог парсинга")
        logs_layout = QVBoxLayout()
        
        # Таблица логов
        self.logs_table = QTableWidget(0, 6)
        self.logs_table.setHorizontalHeaderLabels([
            "Время", "Аккаунт", "Фраза", "Частотность", "Статус", "Скорость"
        ])
        
        header = self.logs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 80)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.resizeSection(1, 100)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.resizeSection(3, 100)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.resizeSection(4, 80)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.resizeSection(5, 100)
        
        logs_layout.addWidget(self.logs_table)
        logs_group.setLayout(logs_layout)
        layout.addWidget(logs_group)
        
        # Статистика внизу
        self.stats_label = QLabel(
            "Обработано: 0 | Успешно: 0 | Ошибок: 0 | Скорость: 0 фраз/мин | Время: 00:00:00"
        )
        layout.addWidget(self.stats_label)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ ЗАПУСТИТЬ ПАРСИНГ")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.start_btn.clicked.connect(self.start_parsing)
        buttons_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ ОСТАНОВИТЬ")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_parsing)
        buttons_layout.addWidget(self.stop_btn)
        
        self.save_btn = QPushButton("💾 Сохранить результаты")
        self.save_btn.clicked.connect(self.save_results)
        buttons_layout.addWidget(self.save_btn)
        
        self.export_btn = QPushButton("📊 Экспорт в CSV")
        self.export_btn.clicked.connect(self.export_csv)
        buttons_layout.addWidget(self.export_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Загружаем аккаунты при старте
        self.load_accounts()
        self.phrases = []
        
    def load_accounts(self):
        """Загрузка списка аккаунтов"""
        self.account_combo.clear()
        self.account_combo.addItem("CDP (Chrome на порту 9222)", None)
        
        accounts = account_service.list_accounts()
        for acc in accounts:
            self.account_combo.addItem(acc.name, acc.id)
    
    def on_headless_toggled(self, checked):
        """При включении headless отключаем визуальный режим"""
        if checked:
            self.visual_check.setChecked(False)
            self.num_browsers_spin.setEnabled(False)
    
    def on_visual_toggled(self, checked):
        """При включении визуального режима отключаем headless"""
        if checked:
            self.headless_check.setChecked(False)
            self.num_browsers_spin.setEnabled(True)
        else:
            self.num_browsers_spin.setEnabled(False)
    
    def auto_login(self):
        """Автоматический логин с запросом секретного вопроса"""
        account_id = self.account_combo.currentData()
        if not account_id:
            QMessageBox.warning(self, "Внимание", "Выберите аккаунт для логина")
            return
        
        # TODO: Реализовать диалог для секретного вопроса
        QMessageBox.information(self, "Автологин", "Функция в разработке")
    
    def load_phrases(self):
        """Загрузка фраз из файла"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл с фразами",
            "",
            "Text files (*.txt);;All files (*.*)"
        )
        
        if filename:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
                self.phrases_text.setPlainText(content)
                
            lines = content.strip().split("\n")
            self.phrases = [line.strip() for line in lines if line.strip()]
            self.phrases_count_label.setText(f"{len(self.phrases)} фраз загружено")
    
    def clear_phrases(self):
        """Очистка списка фраз"""
        self.phrases_text.clear()
        self.phrases = []
        self.phrases_count_label.setText("0 фраз загружено")
    
    def add_log(self, time_str, account, phrase, frequency, status, speed):
        """Добавление записи в лог"""
        row = self.logs_table.rowCount()
        self.logs_table.insertRow(row)
        
        self.logs_table.setItem(row, 0, QTableWidgetItem(time_str))
        self.logs_table.setItem(row, 1, QTableWidgetItem(account))
        self.logs_table.setItem(row, 2, QTableWidgetItem(phrase))
        self.logs_table.setItem(row, 3, QTableWidgetItem(frequency))
        self.logs_table.setItem(row, 4, QTableWidgetItem(status))
        self.logs_table.setItem(row, 5, QTableWidgetItem(speed))
        
        # Прокручиваем к последней записи
        self.logs_table.scrollToBottom()
        
        # Ограничиваем количество записей
        if self.logs_table.rowCount() > 1000:
            self.logs_table.removeRow(0)
    
    def update_stats(self, processed, success, errors, speed, elapsed):
        """Обновление статистики"""
        hours, remainder = divmod(int(elapsed), 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        self.stats_label.setText(
            f"Обработано: {processed} | Успешно: {success} | "
            f"Ошибок: {errors} | Скорость: {speed:.1f} фраз/мин | "
            f"Время: {time_str}"
        )
    
    def on_log_received(self, time_str, account, phrase, frequency, status, speed):
        """Обработчик получения лога от воркера"""
        self.add_log(time_str, account, phrase, frequency, status, speed)
    
    def on_worker_log_message(self, message: str) -> None:
        """Простой текстовый лог от фонового потока"""
        self.add_log(
            datetime.now().strftime("%H:%M:%S"),
            "",
            message,
            "",
            "ℹ️",
            ""
        )
    
    def on_worker_error(self, message: str) -> None:
        """Сообщение об ошибке от фонового потока"""
        self.add_log(
            datetime.now().strftime("%H:%M:%S"),
            "",
            message,
            "",
            "Ошибка",
            ""
        )
    
    def on_stats_received(self, processed, success, errors, speed, elapsed):
        """Обработчик получения статистики от воркера"""
        self.update_stats(processed, success, errors, speed, elapsed)
    
    def on_finished(self, success, message):
        """Обработчик завершения парсинга"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            QMessageBox.information(self, "Готово", message)
        else:
            QMessageBox.warning(self, "Ошибка", message)
        
        self.worker_thread = None
    
    def start_parsing(self):
        """Запуск парсинга"""
        # Получаем фразы из текстового поля
        content = self.phrases_text.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Внимание", "Добавьте фразы для парсинга")
            return
        
        self.phrases = [line.strip() for line in content.split("\n") if line.strip()]
        
        if not self.phrases:
            QMessageBox.warning(self, "Внимание", "Список фраз пуст")
            return
        
        # Получаем выбранный аккаунт
        account_id = self.account_combo.currentData()
        account = None
        if account_id:
            # Найдем аккаунт по id из списка
            accounts = account_service.list_accounts()
            for acc in accounts:
                if acc.id == account_id:
                    account = acc
                    break
        
        # Определяем режим
        if self.turbo_radio.isChecked():
            mode = "turbo"
        elif self.fast_radio.isChecked():
            mode = "fast"
        else:
            mode = "normal"
        
        # Блокируем кнопку старта
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Очищаем логи
        self.logs_table.setRowCount(0)
        
        # Создаем и запускаем воркер
        self.worker_thread = ParserWorkerThread(
            self.phrases,
            account,
            self.headless_check.isChecked(),
            mode,
            visual_mode=self.visual_check.isChecked(),
            num_browsers=self.num_browsers_spin.value()
        )
        
        # Подключаем сигналы
        self.worker_thread.log_signal.connect(self.on_log_received)
        self.worker_thread.log_message.connect(self.on_worker_log_message)
        self.worker_thread.error_signal.connect(self.on_worker_error)
        self.worker_thread.stats_signal.connect(self.on_stats_received)
        self.worker_thread.finished_signal.connect(self.on_finished)
        
        # Запускаем
        self.worker_thread.start()
        
        self.add_log(
            datetime.now().strftime("%H:%M:%S"),
            "",
            f"Запуск парсинга {len(self.phrases)} фраз...",
            "",
            "🚀",
            ""
        )
    
    def stop_parsing(self):
        """Остановка парсинга"""
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        self.add_log(
            datetime.now().strftime("%H:%M:%S"),
            "",
            "Парсинг остановлен",
            "",
            "⏹",
            ""
        )
    
    def save_results(self):
        """Сохранение результатов в БД"""
        QMessageBox.information(self, "Готово", "Результаты автоматически сохраняются в БД")
    
    def export_csv(self):
        """Экспорт результатов в CSV"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить результаты",
            "",
            "CSV files (*.csv);;All files (*.*)"
        )
        
        if filename:
            import csv
            
            with open(filename, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Фраза", "Частотность", "Регион", "Время"])
                
                for row in range(self.logs_table.rowCount()):
                    status = self.logs_table.item(row, 4).text()
                    if status == "✓":
                        writer.writerow([
                            self.logs_table.item(row, 2).text(),  # phrase
                            self.logs_table.item(row, 3).text().replace(",", ""),  # frequency
                            self.region_edit.text(),  # region
                            self.logs_table.item(row, 0).text()  # time
                        ])
            
            QMessageBox.information(self, "Готово", f"Результаты экспортированы в {filename}")


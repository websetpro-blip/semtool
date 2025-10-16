"""
Full Pipeline Tab - полный цикл парсинга Wordstat + Direct + Кластеризация
"""

import csv
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QFileDialog,
    QMessageBox, QHeaderView, QPlainTextEdit, QProgressBar,
    QLineEdit
)

from ..workers.full_pipeline_worker import FullPipelineWorkerThread


class FullPipelineTab(QWidget):
    """Вкладка Full Pipeline: Wordstat → Direct → Clustering → Export"""
    
    def __init__(self):
        super().__init__()
        self.worker_thread = None
        self.results = []
        self.setup_ui()
        
    def setup_ui(self):
        """Создание интерфейса"""
        layout = QVBoxLayout(self)
        
        # Верхняя панель
        control_group = QGroupBox("Full Pipeline: Wordstat → Direct → Кластеризация")
        control_layout = QVBoxLayout()
        
        # Строка 1: Загрузка фраз
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Фразы для парсинга:"))
        
        self.load_btn = QPushButton("📁 Загрузить из файла")
        self.load_btn.clicked.connect(self.load_phrases)
        row1.addWidget(self.load_btn)
        
        self.clear_btn = QPushButton("🗑 Очистить")
        self.clear_btn.clicked.connect(self.clear_phrases)
        row1.addWidget(self.clear_btn)
        
        self.count_label = QLabel("0 фраз")
        row1.addWidget(self.count_label)
        
        row1.addWidget(QLabel("Регион:"))
        self.region_input = QLineEdit("225")
        self.region_input.setMaximumWidth(60)
        row1.addWidget(self.region_input)
        
        row1.addStretch()
        control_layout.addLayout(row1)
        
        # Строка 2: Кнопки управления
        row2 = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 ЗАПУСТИТЬ FULL PIPELINE")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.start_btn.clicked.connect(self.start_pipeline)
        row2.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ ОСТАНОВИТЬ")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 12px;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_pipeline)
        row2.addWidget(self.stop_btn)
        
        self.export_btn = QPushButton("💾 Экспорт CSV")
        self.export_btn.clicked.connect(self.export_csv)
        row2.addWidget(self.export_btn)
        
        row2.addStretch()
        control_layout.addLayout(row2)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Текстовое поле для фраз
        phrases_group = QGroupBox("Фразы (по одной на строку)")
        phrases_layout = QVBoxLayout()
        
        self.phrases_text = QPlainTextEdit()
        self.phrases_text.setPlaceholderText("Введите или загрузите фразы...\nПример:\nкупить телефон\nкупить iphone\nкупить samsung")
        self.phrases_text.setMaximumHeight(120)
        phrases_layout.addWidget(self.phrases_text)
        
        phrases_group.setLayout(phrases_layout)
        layout.addWidget(phrases_group)
        
        # Прогресс бар
        progress_group = QGroupBox("Прогресс")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Готов к запуску")
        progress_layout.addWidget(self.progress_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Таблица результатов с НОВЫМИ колонками
        results_group = QGroupBox("Результаты Full Pipeline")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget(0, 8)
        self.results_table.setHorizontalHeaderLabels([
            "Время", "Фраза", "Частотность", "CPC (₽)", "Показы", "Бюджет (₽)", "Группа", "Статус"
        ])
        
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 80)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.resizeSection(2, 100)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.resizeSection(3, 80)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.resizeSection(4, 90)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.resizeSection(5, 100)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        header.resizeSection(6, 120)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        header.resizeSection(7, 60)
        
        results_layout.addWidget(self.results_table)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Статистика внизу
        self.stats_label = QLabel(
            "Обработано: 0 | Успешно: 0 | Скорость: 0 фраз/мин | Время: 00:00"
        )
        layout.addWidget(self.stats_label)
        
    def load_phrases(self):
        """Загрузка фраз из файла"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл с фразами", "", "Text files (*.txt);;All files (*.*)"
        )
        
        if filename:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
                self.phrases_text.setPlainText(content)
            
            lines = content.strip().split("\n")
            phrases = [line.strip() for line in lines if line.strip()]
            self.count_label.setText(f"{len(phrases)} фраз")
    
    def clear_phrases(self):
        """Очистка фраз"""
        self.phrases_text.clear()
        self.count_label.setText("0 фраз")
    
    def start_pipeline(self):
        """Запуск Full Pipeline"""
        content = self.phrases_text.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Внимание", "Добавьте фразы для парсинга")
            return
        
        phrases = [line.strip() for line in content.split("\n") if line.strip()]
        if not phrases:
            QMessageBox.warning(self, "Внимание", "Список фраз пуст")
            return
        
        # Очищаем таблицу
        self.results_table.setRowCount(0)
        self.results = []
        
        # Блокируем кнопки
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Создаем и запускаем worker
        region = int(self.region_input.text()) if self.region_input.text().isdigit() else 225
        self.worker_thread = FullPipelineWorkerThread(phrases, region=region)
        
        # Подключаем сигналы
        self.worker_thread.log_signal.connect(self.add_log_row)
        self.worker_thread.log_message.connect(self.on_log_message)
        self.worker_thread.error_signal.connect(self.on_error)
        self.worker_thread.progress_signal.connect(self.on_progress)
        self.worker_thread.stats_signal.connect(self.on_stats)
        self.worker_thread.finished_signal.connect(self.on_finished)
        self.worker_thread.results_ready.connect(self.on_results_ready)
        
        # Запускаем
        self.worker_thread.start()
        
        self.progress_label.setText(f"Запуск парсинга {len(phrases)} фраз...")
    
    def stop_pipeline(self):
        """Остановка парсинга"""
        if self.worker_thread:
            self.worker_thread.cancel()
            self.worker_thread.quit()
            self.worker_thread.wait()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_label.setText("Остановлено пользователем")
    
    def add_log_row(self, time_str, phrase, freq, cpc, impressions, budget, stem, status):
        """Добавление строки в таблицу"""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        self.results_table.setItem(row, 0, QTableWidgetItem(time_str))
        self.results_table.setItem(row, 1, QTableWidgetItem(phrase))
        self.results_table.setItem(row, 2, QTableWidgetItem(freq))
        self.results_table.setItem(row, 3, QTableWidgetItem(cpc))
        self.results_table.setItem(row, 4, QTableWidgetItem(impressions))
        self.results_table.setItem(row, 5, QTableWidgetItem(budget))
        self.results_table.setItem(row, 6, QTableWidgetItem(stem))
        self.results_table.setItem(row, 7, QTableWidgetItem(status))
        
        # Прокручиваем к последней записи
        self.results_table.scrollToBottom()
    
    def on_log_message(self, message):
        """Логирование сообщений"""
        self.progress_label.setText(message)
    
    def on_error(self, error):
        """Обработка ошибок"""
        QMessageBox.critical(self, "Ошибка", error)
    
    def on_progress(self, current, total, stage):
        """Обновление прогресса"""
        if total > 0:
            percent = int(current / total * 100)
            self.progress_bar.setValue(percent)
            self.progress_label.setText(f"{stage}: {current}/{total} ({percent}%)")
    
    def on_stats(self, processed, success, errors, speed, elapsed):
        """Обновление статистики"""
        mins, secs = divmod(int(elapsed), 60)
        self.stats_label.setText(
            f"Обработано: {processed} | Успешно: {success} | "
            f"Скорость: {speed:.1f} фраз/мин | Время: {mins:02d}:{secs:02d}"
        )
    
    def on_results_ready(self, results):
        """Сохранение полных результатов"""
        self.results = results
    
    def on_finished(self, success, message):
        """Завершение работы"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100 if success else 0)
        
        if success:
            QMessageBox.information(self, "Готово", message)
        else:
            QMessageBox.warning(self, "Ошибка", message)
    
    def export_csv(self):
        """Экспорт результатов в CSV"""
        if not self.results:
            QMessageBox.warning(self, "Внимание", "Нет данных для экспорта")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить результаты", 
            f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV files (*.csv);;All files (*.*)"
        )
        
        if filename:
            with open(filename, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow([
                    "Фраза", "Частотность", "CPC", "Показы", "Бюджет", 
                    "Группа", "Размер группы", "Средняя частота группы", "Общий бюджет группы"
                ])
                
                for item in self.results:
                    writer.writerow([
                        item.get('phrase', ''),
                        item.get('freq', 0),
                        item.get('cpc', 0),
                        item.get('impressions', 0),
                        item.get('budget', 0),
                        item.get('stem', ''),
                        item.get('group_size', 1),
                        round(item.get('group_avg_freq', 0), 2),
                        round(item.get('group_total_budget', 0), 2),
                    ])
            
            QMessageBox.information(
                self, "Готово", 
                f"Экспортировано {len(self.results)} записей в {filename}"
            )

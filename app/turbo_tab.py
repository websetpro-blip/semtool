"""
ТУРБО ПАРСЕР TAB - GUI вкладка для турбо парсинга
Интерфейс как в DirectParser с таблицей логов
"""

import asyncio
import threading
import time
from pathlib import Path
from datetime import datetime
import json

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
    QCheckBox, QSpinBox, QComboBox, QFileDialog, QMessageBox,
    QHeaderView, QRadioButton, QButtonGroup, QLineEdit
)

from ..services.accounts import AccountsService
from ..workers.turbo_parser_integration import TurboWordstatParser


class TurboParserTab(QWidget):
    """Вкладка турбо парсера с интерфейсом как в DirectParser"""
    
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.accounts_service = AccountsService(db)
        self.parser = None
        self.parsing_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        """Создание интерфейса вкладки"""
        
        # Верхняя панель управления
        control_frame = ttk.LabelFrame(self, text="Управление парсингом", padding=10)
        control_frame.pack(fill="x", padx=5, pady=5)
        
        # Строка 1: Выбор аккаунтов
        row1 = ttk.Frame(control_frame)
        row1.pack(fill="x", pady=2)
        
        ttk.Label(row1, text="Аккаунты:").pack(side="left", padx=(0, 5))
        
        # Таблица аккаунтов с чекбоксами
        acc_frame = ttk.Frame(row1)
        acc_frame.pack(side="left", fill="x", expand=True)
        
        self.accounts_tree = ttk.Treeview(acc_frame, columns=("proxy", "status"), height=5)
        self.accounts_tree.heading("#0", text="Аккаунт")
        self.accounts_tree.heading("proxy", text="Прокси")
        self.accounts_tree.heading("status", text="Статус")
        self.accounts_tree.column("#0", width=150)
        self.accounts_tree.column("proxy", width=200)
        self.accounts_tree.column("status", width=100)
        self.accounts_tree.pack(side="left", fill="both", expand=True)
        
        acc_scroll = ttk.Scrollbar(acc_frame, orient="vertical", command=self.accounts_tree.yview)
        acc_scroll.pack(side="right", fill="y")
        self.accounts_tree.configure(yscrollcommand=acc_scroll.set)
        
        # Кнопки управления аккаунтами
        acc_buttons = ttk.Frame(row1)
        acc_buttons.pack(side="left", padx=5)
        
        ttk.Button(acc_buttons, text="Обновить", command=self.load_accounts).pack(pady=2)
        ttk.Button(acc_buttons, text="Автологин", command=self.auto_login).pack(pady=2)
        
        # Строка 2: Настройки парсинга
        row2 = ttk.Frame(control_frame)
        row2.pack(fill="x", pady=5)
        
        ttk.Label(row2, text="Режим:").pack(side="left", padx=(0, 5))
        self.mode_var = tk.StringVar(value="turbo")
        modes = [
            ("Турбо (195 фраз/мин)", "turbo"),
            ("Быстрый (100 фраз/мин)", "fast"),
            ("Обычный (20 фраз/мин)", "normal")
        ]
        for text, value in modes:
            ttk.Radiobutton(row2, text=text, variable=self.mode_var, value=value).pack(side="left", padx=5)
        
        ttk.Label(row2, text="Регион:").pack(side="left", padx=(20, 5))
        self.region_var = tk.StringVar(value="225")
        region_entry = ttk.Entry(row2, textvariable=self.region_var, width=10)
        region_entry.pack(side="left")
        
        ttk.Label(row2, text="Потоков:").pack(side="left", padx=(20, 5))
        self.threads_var = tk.IntVar(value=1)
        threads_spin = ttk.Spinbox(row2, from_=1, to=10, textvariable=self.threads_var, width=5)
        threads_spin.pack(side="left")
        
        self.headless_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="Фоновый режим", variable=self.headless_var).pack(side="left", padx=20)
        
        # Строка 3: Загрузка фраз
        row3 = ttk.Frame(control_frame)
        row3.pack(fill="x", pady=5)
        
        ttk.Label(row3, text="Фразы:").pack(side="left", padx=(0, 5))
        ttk.Button(row3, text="Загрузить из файла", command=self.load_phrases).pack(side="left", padx=5)
        ttk.Button(row3, text="Очистить", command=self.clear_phrases).pack(side="left", padx=5)
        
        self.phrases_count = ttk.Label(row3, text="0 фраз загружено")
        self.phrases_count.pack(side="left", padx=20)
        
        # Текстовое поле для фраз
        phrases_frame = ttk.LabelFrame(self, text="Фразы для парсинга", padding=5)
        phrases_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.phrases_text = scrolledtext.ScrolledText(phrases_frame, height=10, width=80)
        self.phrases_text.pack(fill="both", expand=True)
        
        # Панель логов (как в DirectParser)
        logs_frame = ttk.LabelFrame(self, text="Лог парсинга", padding=5)
        logs_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Таблица логов
        columns = ("time", "account", "phrase", "frequency", "status", "speed")
        self.logs_tree = ttk.Treeview(logs_frame, columns=columns, show="headings", height=15)
        
        self.logs_tree.heading("time", text="Время")
        self.logs_tree.heading("account", text="Аккаунт")
        self.logs_tree.heading("phrase", text="Фраза")
        self.logs_tree.heading("frequency", text="Частотность")
        self.logs_tree.heading("status", text="Статус")
        self.logs_tree.heading("speed", text="Скорость")
        
        self.logs_tree.column("time", width=100)
        self.logs_tree.column("account", width=100)
        self.logs_tree.column("phrase", width=200)
        self.logs_tree.column("frequency", width=100)
        self.logs_tree.column("status", width=80)
        self.logs_tree.column("speed", width=100)
        
        self.logs_tree.pack(side="left", fill="both", expand=True)
        
        logs_scroll = ttk.Scrollbar(logs_frame, orient="vertical", command=self.logs_tree.yview)
        logs_scroll.pack(side="right", fill="y")
        self.logs_tree.configure(yscrollcommand=logs_scroll.set)
        
        # Статистика внизу
        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill="x", padx=5, pady=5)
        
        self.stats_label = ttk.Label(stats_frame, 
            text="Обработано: 0 | Успешно: 0 | Ошибок: 0 | Скорость: 0 фраз/мин | Время: 00:00:00")
        self.stats_label.pack(side="left")
        
        # Кнопки управления
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill="x", padx=5, pady=5)
        
        self.start_btn = ttk.Button(buttons_frame, text="▶ ЗАПУСТИТЬ ПАРСИНГ", 
                                    command=self.start_parsing, style="Accent.TButton")
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ttk.Button(buttons_frame, text="⏹ ОСТАНОВИТЬ", 
                                   command=self.stop_parsing, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        ttk.Button(buttons_frame, text="💾 Сохранить результаты", 
                  command=self.save_results).pack(side="left", padx=5)
        
        ttk.Button(buttons_frame, text="📊 Экспорт в CSV", 
                  command=self.export_csv).pack(side="left", padx=5)
        
        # Загружаем аккаунты при старте
        self.load_accounts()
        self.phrases = []
        
    def load_accounts(self):
        """Загрузка списка аккаунтов"""
        self.accounts_tree.delete(*self.accounts_tree.get_children())
        
        accounts = self.accounts_service.get_all()
        for acc in accounts:
            proxy = acc.proxy if acc.proxy else "Без прокси"
            status = acc.status if acc.status else "ok"
            
            self.accounts_tree.insert("", "end", 
                                     text=acc.name,
                                     values=(proxy, status))
    
    def auto_login(self):
        """Автоматический логин с запросом секретного вопроса"""
        selected = self.accounts_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите аккаунт для логина")
            return
        
        account_name = self.accounts_tree.item(selected[0])["text"]
        
        # Диалог для секретного вопроса
        dialog = tk.Toplevel(self)
        dialog.title("Автологин")
        dialog.geometry("400x200")
        
        ttk.Label(dialog, text=f"Логин в аккаунт: {account_name}").pack(pady=10)
        ttk.Label(dialog, text="Если потребуется, введите ответ на секретный вопрос:").pack(pady=5)
        
        answer_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=answer_var, width=40).pack(pady=10)
        
        def start_login():
            answer = answer_var.get()
            dialog.destroy()
            
            # Запускаем автологин в отдельном потоке
            self.add_log("", account_name, "Запуск автологина...", "", "⏳", "")
            # TODO: Реализовать автологин через Playwright
            
        ttk.Button(dialog, text="Начать логин", command=start_login).pack(pady=10)
        
    def load_phrases(self):
        """Загрузка фраз из файла"""
        filename = filedialog.askopenfilename(
            title="Выберите файл с фразами",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
                self.phrases_text.delete("1.0", "end")
                self.phrases_text.insert("1.0", content)
                
            lines = content.strip().split("\n")
            self.phrases = [line.strip() for line in lines if line.strip()]
            self.phrases_count.config(text=f"{len(self.phrases)} фраз загружено")
    
    def clear_phrases(self):
        """Очистка списка фраз"""
        self.phrases_text.delete("1.0", "end")
        self.phrases = []
        self.phrases_count.config(text="0 фраз загружено")
    
    def add_log(self, time_str, account, phrase, frequency, status, speed):
        """Добавление записи в лог"""
        if not time_str:
            time_str = datetime.now().strftime("%H:%M:%S")
        
        self.logs_tree.insert("", 0, values=(
            time_str, account, phrase, frequency, status, speed
        ))
        
        # Ограничиваем количество записей в логе
        children = self.logs_tree.get_children()
        if len(children) > 1000:
            self.logs_tree.delete(children[-1])
    
    def update_stats(self, processed, success, errors, speed, elapsed):
        """Обновление статистики"""
        hours, remainder = divmod(int(elapsed), 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        self.stats_label.config(
            text=f"Обработано: {processed} | Успешно: {success} | "
                 f"Ошибок: {errors} | Скорость: {speed:.1f} фраз/мин | "
                 f"Время: {time_str}"
        )
    
    async def run_parser_async(self):
        """Асинхронный запуск парсера"""
        # Получаем выбранные аккаунты
        selected = self.accounts_tree.selection()
        if not selected:
            account = None
        else:
            account_name = self.accounts_tree.item(selected[0])["text"]
            account = self.accounts_service.get_by_name(account_name)
        
        # Создаем парсер
        headless = self.headless_var.get()
        self.parser = TurboWordstatParser(account=account, headless=headless)
        
        # Настраиваем режим
        mode = self.mode_var.get()
        if mode == "turbo":
            self.parser.num_tabs = 10
        elif mode == "fast":
            self.parser.num_tabs = 5
        else:
            self.parser.num_tabs = 1
        
        try:
            # Запускаем парсинг
            results = await self.parser.parse_batch(self.phrases)
            
            # Обновляем логи с результатами
            for result in results:
                self.add_log(
                    "",
                    account.name if account else "default",
                    result['query'],
                    f"{result['frequency']:,}",
                    "✓",
                    f"{self.parser.total_processed / (time.time() - self.parser.start_time) * 60:.1f}"
                )
            
            messagebox.showinfo("Готово", f"Парсинг завершен! Обработано {len(results)} фраз")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при парсинге: {str(e)}")
            
        finally:
            await self.parser.close()
            self.parser = None
    
    def parsing_worker(self):
        """Воркер для запуска асинхронного парсера в отдельном потоке"""
        asyncio.run(self.run_parser_async())
        
        # После завершения
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
    
    def start_parsing(self):
        """Запуск парсинга"""
        # Получаем фразы из текстового поля
        content = self.phrases_text.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("Внимание", "Добавьте фразы для парсинга")
            return
        
        self.phrases = [line.strip() for line in content.split("\n") if line.strip()]
        
        if not self.phrases:
            messagebox.showwarning("Внимание", "Список фраз пуст")
            return
        
        # Блокируем кнопку старта
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        
        # Очищаем логи
        self.logs_tree.delete(*self.logs_tree.get_children())
        
        # Запускаем парсинг в отдельном потоке
        self.parsing_thread = threading.Thread(target=self.parsing_worker)
        self.parsing_thread.daemon = True
        self.parsing_thread.start()
        
        self.add_log("", "", f"Запуск парсинга {len(self.phrases)} фраз...", "", "🚀", "")
    
    def stop_parsing(self):
        """Остановка парсинга"""
        if self.parser:
            # TODO: Реализовать graceful shutdown
            pass
        
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        
        self.add_log("", "", "Парсинг остановлен", "", "⏹", "")
    
    def save_results(self):
        """Сохранение результатов в БД"""
        # Результаты уже сохраняются автоматически в parse_batch
        messagebox.showinfo("Готово", "Результаты сохранены в БД")
    
    def export_csv(self):
        """Экспорт результатов в CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            import csv
            
            with open(filename, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Фраза", "Частотность", "Регион", "Время"])
                
                for child in self.logs_tree.get_children():
                    values = self.logs_tree.item(child)["values"]
                    if len(values) >= 4 and values[4] == "✓":
                        writer.writerow([
                            values[2],  # phrase
                            values[3].replace(",", ""),  # frequency
                            self.region_var.get(),  # region
                            values[0]  # time
                        ])
            
            messagebox.showinfo("Готово", f"Результаты экспортированы в {filename}")

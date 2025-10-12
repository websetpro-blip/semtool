"""
Расширенная вкладка управления аккаунтами с функцией логина

ПРАВИЛО №1: НЕ ЛОМАТЬ ТО ЧТО РАБОТАЕТ!
- Не удалять рабочие функции
- Не изменять работающую логику
- Не трогать то, что пользователь не просил менять
"""

import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QDialog,
    QProgressBar, QLabel, QGroupBox, QCheckBox,
    QLineEdit, QInputDialog, QFileDialog
)

from ..services import accounts as account_service
from ..workers.visual_browser_manager import VisualBrowserManager, BrowserStatus
# Старый worker больше не используется, теперь CDP подход


class AutoLoginThread(QThread):
    """Поток для автоматической авторизации аккаунта"""
    status_signal = Signal(str)  # Статус операции
    progress_signal = Signal(int)  # Прогресс 0-100
    secret_question_signal = Signal(str, str)  # account_name, question_text
    finished_signal = Signal(bool, str)  # success, message
    
    def __init__(self, account, parent=None):
        super().__init__(parent)
        self.account = account
        self.secret_answer = None
        
    def set_secret_answer(self, answer):
        """Установить ответ на секретный вопрос"""
        self.secret_answer = answer
        
    def run(self):
        """Запуск умного автологина на основе решения GPT"""
        from ..workers.yandex_smart_login import YandexSmartLogin
        import asyncio
        import json
        from pathlib import Path
        
        # Берем профиль ИЗ БАЗЫ ДАННЫХ, а не создаем новый
        profile_path = self.account.profile_path
        
        # ⚠️ ПРОВЕРКА: Профиль ДОЛЖЕН быть из БД!
        if not profile_path:
            self.status_signal.emit(f"[ERROR] У аккаунта {self.account.name} НЕТ profile_path в БД!")
            self.finished_signal.emit(False, "Профиль не указан в БД")
            return
        
        self.status_signal.emit(f"[OK] Профиль из БД: {profile_path}")
        
        # Если путь относительный - делаем полным
        if not profile_path.startswith("C:"):
            profile_path = f"C:/AI/yandex/{profile_path}"
            self.status_signal.emit(f"[INFO] Путь преобразован: {profile_path}")
        
        # Загружаем логин и пароль из accounts.json
        accounts_file = Path("C:/AI/yandex/configs/accounts.json")
        if not accounts_file.exists():
            self.status_signal.emit(f"[ERROR] Файл accounts.json не найден!")
            self.finished_signal.emit(False, "Файл accounts.json не найден")
            return
        
        with open(accounts_file, 'r', encoding='utf-8') as f:
            accounts_data = json.load(f)
            account_info = None
            for acc in accounts_data:
                if acc["login"] == self.account.name:
                    account_info = acc
                    break
        
        if not account_info:
            self.status_signal.emit(f"[ERROR] Аккаунт {self.account.name} не найден в accounts.json!")
            self.finished_signal.emit(False, f"Аккаунт не найден в accounts.json")
            return
        
        self.status_signal.emit(f"[CDP] Запуск автологина для {self.account.name}...")
        
        # Получаем secret_answer из accounts.json если есть
        secret_answer = self.secret_answer  # Пользователь мог ввести вручную
        if not secret_answer and "secret" in account_info and account_info["secret"]:
            secret_answer = account_info["secret"]
            self.status_signal.emit(f"[CDP] Найден сохраненный ответ на секретный вопрос")
        
        # Используем РАЗНЫЕ порты для разных аккаунтов!
        # Генерируем порт на основе хеша имени аккаунта
        port = 9222 + (hash(self.account.name) % 100)
        self.status_signal.emit(f"[CDP] Используется порт {port} для {self.account.name}")
        
        # Создаем умный автологин
        smart_login = YandexSmartLogin()
        
        # Подключаем сигналы для отправки статусов
        smart_login.status_update.connect(self.status_signal.emit)
        smart_login.progress_update.connect(self.progress_signal.emit)
        smart_login.secret_question_required.connect(self.secret_question_signal.emit)
        
        # Если есть ответ от пользователя - устанавливаем
        if self.secret_answer:
            smart_login.set_secret_answer(self.secret_answer)
        
        # Получаем прокси из accounts.json
        proxy_to_use = account_info.get("proxy", None)
        if proxy_to_use:
            self.status_signal.emit(f"[INFO] Используется прокси: {proxy_to_use.split('@')[0]}@***")
        
        # Запускаем умный автологин
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            self.status_signal.emit(f"[SMART] Запускаю автологин...")
            success = loop.run_until_complete(smart_login.login(
                account_name=self.account.name,
                profile_path=profile_path,
                proxy=proxy_to_use  # Используем прокси из accounts.json!
            ))
            
            if success:
                self.status_signal.emit(f"[OK] Автологин успешен для {self.account.name}!")
                self.finished_signal.emit(True, "Авторизация успешна")
            else:
                self.status_signal.emit(f"[ERROR] Автологин не удался для {self.account.name}")
                self.finished_signal.emit(False, "Ошибка авторизации")
                
        except Exception as e:
            self.status_signal.emit(f"[ERROR] {e}")
            self.finished_signal.emit(False, str(e))
        finally:
            loop.close()


class LoginWorkerThread(QThread):
    """Поток для логина в браузеры"""
    progress_signal = Signal(str)  # Сообщение о прогрессе
    account_logged_signal = Signal(int, bool, str)  # account_id, success, message
    finished_signal = Signal(bool, str)  # success, message
    
    def __init__(self, accounts_to_login, parent=None, check_only=False, visual_mode=False):
        super().__init__(parent)
        self.accounts = accounts_to_login
        self.manager = None
        self.check_only = check_only  # Только проверка без открытия браузеров
        self.visual_mode = visual_mode  # Визуальный режим - всегда открывать браузеры
        
    def run(self):
        """Запуск логина в отдельном потоке"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self.login_accounts())
        except Exception as e:
            self.finished_signal.emit(False, str(e))
        finally:
            loop.close()
    
    async def login_accounts(self):
        """Логин в аккаунты"""
        from ..workers.auth_checker import AuthChecker
        
        # Отладка - показываем сколько аккаунтов получили
        self.progress_signal.emit(f"Received {len(self.accounts)} accounts for processing")
        self.progress_signal.emit(f"Accounts: {[acc.name if hasattr(acc, 'name') else str(acc) for acc in self.accounts]}")
        
        self.progress_signal.emit(f"Checking authorization for {len(self.accounts)} accounts...")
        
        # Сначала проверяем авторизацию через Wordstat
        auth_checker = AuthChecker()
        accounts_to_check = []
        
        for acc in self.accounts:
            # Используем абсолютные пути для Windows
            if acc.profile_path:
                profile = str(Path(acc.profile_path).absolute()).replace("\\", "/")
            else:
                profile = str(Path(f"C:/AI/yandex/.profiles/{acc.name}").absolute()).replace("\\", "/")
            accounts_to_check.append({
                "name": acc.name,
                "profile_path": profile,
                "proxy": acc.proxy,
                "account_id": acc.id
            })
        
        # Проверяем авторизацию
        self.progress_signal.emit("Testing authorization via Wordstat...")
        auth_results = await auth_checker.check_multiple_accounts(accounts_to_check)
        
        # Фильтруем кто нуждается в логине
        need_login = []
        already_authorized = []
        
        for acc_data in accounts_to_check:
            acc_name = acc_data["name"]
            result = auth_results.get(acc_name, {})
            
            if result.get("is_authorized"):
                already_authorized.append(acc_name)
                self.progress_signal.emit(f"[OK] {acc_name}: Already authorized")
                # Обновляем статус в БД
                self.account_logged_signal.emit(acc_data["account_id"], True, "Authorized")
            else:
                need_login.append(acc_data)
                self.progress_signal.emit(f"[!] {acc_name}: Login required")
        
        if already_authorized:
            self.progress_signal.emit(f"Authorized: {', '.join(already_authorized)}")
        
        if not need_login:
            self.progress_signal.emit("All accounts are authorized!")
            # В визуальном режиме открываем браузеры даже если все авторизованы
            if self.visual_mode:
                self.progress_signal.emit("Opening browsers for visual parsing...")
                need_login = accounts_to_check  # Открываем браузеры для всех аккаунтов
            elif not self.check_only:
                self.progress_signal.emit("Opening browsers for visual parsing...")
                need_login = accounts_to_check  # Открываем браузеры для всех аккаунтов
            else:
                self.finished_signal.emit(True, f"All {len(self.accounts)} accounts are authorized")
                return
        
        # Если есть кто требует логина или нужны браузеры для парсинга
        if not self.check_only:
            self.progress_signal.emit(f"Opening {len(need_login)} browsers...")
            
            # Создаем менеджер браузеров
            self.manager = VisualBrowserManager(num_browsers=len(need_login))
            
            try:
                # Запускаем браузеры только для тех кто не авторизован
                await self.manager.start_all_browsers(need_login)
                
                self.progress_signal.emit("Browsers opened. Waiting for login...")
                self.progress_signal.emit("Please login in each opened browser!")
                
                # Ждем логина
                logged_in = await self.manager.wait_for_all_logins(timeout=300)
                
                if logged_in:
                    # Обновляем статус аккаунтов
                    for browser_id, browser in self.manager.browsers.items():
                        if browser.status == BrowserStatus.LOGGED_IN:
                            # Находим account_id из need_login
                            if browser_id < len(need_login):
                                acc_data = need_login[browser_id]
                                self.account_logged_signal.emit(
                                    acc_data['account_id'], 
                                    True, 
                                    "Logged in"
                                )
                    
                    self.finished_signal.emit(True, "All accounts logged in!")
                else:
                    self.finished_signal.emit(False, "Not all accounts logged in")
                    
            except Exception as e:
                self.progress_signal.emit(f"Error: {str(e)}")
                self.finished_signal.emit(False, str(e))
                
            finally:
                if self.manager:
                    await self.manager.close_all()


class AccountsTabExtended(QWidget):
    """Расширенная вкладка аккаунтов с функцией логина"""
    accounts_changed = Signal()
    
    def __init__(self):
        super().__init__()
        self.login_thread = None
        self._current_login_index = 0
        self.setup_ui()
        
    def setup_ui(self):
        """Создание интерфейса"""
        layout = QVBoxLayout(self)
        
        # Верхняя панель с кнопками управления
        buttons_layout = QHBoxLayout()
        
        # Стандартные кнопки
        self.add_btn = QPushButton("➕ Добавить")
        self.add_btn.clicked.connect(self.add_account)
        buttons_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("✏️ Изменить")
        self.edit_btn.clicked.connect(self.edit_account)
        self.edit_btn.setEnabled(False)
        buttons_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ Удалить")
        self.delete_btn.clicked.connect(self.delete_account)
        self.delete_btn.setEnabled(False)
        buttons_layout.addWidget(self.delete_btn)
        
        self.import_btn = QPushButton("📥 Импорт")
        self.import_btn.clicked.connect(self.import_accounts)
        buttons_layout.addWidget(self.import_btn)
        
        buttons_layout.addStretch()
        
        # Новые кнопки для логина
        self.login_btn = QPushButton("🔐 Войти")
        self.login_btn.clicked.connect(self.login_selected)
        self.login_btn.setEnabled(False)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        buttons_layout.addWidget(self.login_btn)
        
        # Кнопка автоматического логина
        self.auto_login_btn = QPushButton("Автологин")
        self.auto_login_btn.clicked.connect(self.auto_login_selected)
        self.auto_login_btn.setEnabled(False)
        self.auto_login_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.auto_login_btn.setToolTip("Автоматическая авторизация с вводом логина и пароля")
        buttons_layout.addWidget(self.auto_login_btn)
        
        self.login_all_btn = QPushButton("🔐 Войти во все")
        self.login_all_btn.clicked.connect(self.launch_browsers_cdp)
        self.login_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #0976d2;
            }
        """)
        buttons_layout.addWidget(self.login_all_btn)
        
        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.clicked.connect(self.refresh)
        buttons_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(buttons_layout)
        
        # Панель управления браузерами
        browser_panel = QGroupBox("Browser Management")
        browser_layout = QHBoxLayout()
        
        self.open_browsers_btn = QPushButton("🌐 Открыть браузеры для логина")
        self.open_browsers_btn.clicked.connect(self.open_browsers_for_login)
        self.open_browsers_btn.setToolTip("Открыть браузеры только для тех аккаунтов, где нужен логин")
        browser_layout.addWidget(self.open_browsers_btn)
        
        self.browser_status_btn = QPushButton("📊 Состояние браузеров")
        self.browser_status_btn.clicked.connect(self.show_browser_status)
        self.browser_status_btn.setToolTip("Показать статус всех открытых браузеров")
        browser_layout.addWidget(self.browser_status_btn)
        
        self.update_status_btn = QPushButton("🔄 Обновить статусы")
        self.update_status_btn.clicked.connect(self.update_browser_status)
        self.update_status_btn.setToolTip("Проверить залогинены ли браузеры")
        browser_layout.addWidget(self.update_status_btn)
        
        self.minimize_browsers_btn = QPushButton("📉 Минимизировать браузеры")
        self.minimize_browsers_btn.clicked.connect(self.minimize_all_browsers)
        self.minimize_browsers_btn.setToolTip("Свернуть все браузеры в панель задач")
        browser_layout.addWidget(self.minimize_browsers_btn)
        
        self.close_browsers_btn = QPushButton("❌ Закрыть браузеры")
        self.close_browsers_btn.clicked.connect(self.close_all_browsers)
        self.close_browsers_btn.setToolTip("Закрыть все открытые браузеры")
        browser_layout.addWidget(self.close_browsers_btn)
        
        browser_panel.setLayout(browser_layout)
        layout.addWidget(browser_panel)
        
        # Браузер менеджер
        self.browser_manager = None
        self.browser_thread = None
        
        # Таблица аккаунтов
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "✓",  # Чекбокс
            "Аккаунт",
            "Статус",
            "Авторизация",  # Изменено с "Логин"
            "Профиль",
            "Выбор профиля",  # Добавлено - выбор профиля для парсинга
            "Прокси",
            "Активность",  # Изменено с "Последнее использование"
            "Куки"  # Изменено с "Заметки" - для ручного ввода куков
        ])
        
        # Обработчик двойного клика
        self.table.cellDoubleClicked.connect(self.on_table_double_click)
        
        # Добавляем чекбокс "Выбрать все" в заголовок
        self.select_all_checkbox = QCheckBox()
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)
        # Установим чекбокс в заголовок после создания строк в refresh()
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 30)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.Stretch)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self.table.itemDoubleClicked.connect(self.on_table_double_click)
        
        layout.addWidget(self.table)
        
        # Панель статуса логина с мини-логом
        status_group = QGroupBox("Status and Activity")
        status_layout = QVBoxLayout()
        
        self.login_progress = QProgressBar()
        self.login_progress.setVisible(False)
        status_layout.addWidget(self.login_progress)
        
        self.login_status_label = QLabel("Готов к работе")
        status_layout.addWidget(self.login_status_label)
        
        # Мини-лог для отображения активности
        from PySide6.QtWidgets import QTextEdit
        self.mini_log = QTextEdit()
        self.mini_log.setMaximumHeight(100)
        self.mini_log.setReadOnly(True)
        self.mini_log.setPlaceholderText("Здесь будет отображаться активность...")
        status_layout.addWidget(self.mini_log)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Инициализация
        self._accounts = []
        self.refresh()
    
    def toggle_select_all(self, state):
        """Переключить выбор всех аккаунтов"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(state == 2)  # 2 = Qt.Checked
        self.log_action(f"{'Выбраны' if state == 2 else 'Сняты'} все аккаунты")
    
    def log_action(self, message):
        """Добавить сообщение в мини-лог"""
        from datetime import datetime
        from PySide6.QtGui import QTextCursor
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.mini_log.append(f"[{timestamp}] {message}")
        # Прокручиваем вниз
        cursor = self.mini_log.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.mini_log.setTextCursor(cursor)
    
    def _selected_rows(self) -> List[int]:
        """Получить выбранные строки"""
        selected = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected.append(row)
        return selected
    
    def _current_account(self) -> Optional[Any]:
        """Получить текущий выбранный аккаунт"""
        row = self.table.currentRow()
        if 0 <= row < len(self._accounts):
            return self._accounts[row]
        return None
    
    def _update_buttons(self):
        """Обновить состояние кнопок"""
        has_selection = self._current_account() is not None
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        
        selected_rows = self._selected_rows()
        self.login_btn.setEnabled(len(selected_rows) > 0)
        # Автологин работает только для одного выбранного аккаунта
        self.auto_login_btn.setEnabled(len(selected_rows) == 1)
    
    def refresh(self):
        """Обновить таблицу аккаунтов"""
        # Получаем аккаунты и фильтруем demo_account и wordstat_main (это профиль, а не аккаунт)
        all_accounts = account_service.list_accounts()
        self._accounts = [acc for acc in all_accounts if acc.name not in ["demo_account", "wordstat_main"]]
        self.table.setRowCount(len(self._accounts))
        
        self.log_action(f"Загружено: {len(self._accounts)} аккаунтов")
        
        for row, account in enumerate(self._accounts):
            # Чекбокс
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self._update_buttons)
            self.table.setCellWidget(row, 0, checkbox)
            
            # Создаем комбобокс для выбора профиля
            from PySide6.QtWidgets import QComboBox
            profile_combo = QComboBox()
            # Каждый аккаунт использует СВОЙ профиль - не смешиваем куки!
            available_profiles = []
            if account.name in ["dsmismirnov", "kuznepetya", "vfefyodorov", "volkovsvolkow", "semenovmsemionov"]:
                available_profiles.append(f"{account.name} (основной)")
            # Можем добавить wordstat_main как опцию, но НЕ по умолчанию
            available_profiles.append("wordstat_main (общий - не рекомендуется)")
            profile_combo.addItems(available_profiles)
            
            # Устанавливаем профиль самого аккаунта по умолчанию
            profile_combo.setCurrentIndex(0)  # Профиль аккаунта
            
            # Сохраняем выбранный профиль при изменении
            profile_combo.currentTextChanged.connect(lambda text: self._update_profile(account.id, text))
            
            # Данные аккаунта
            items = [
                QTableWidgetItem(account.name),
                QTableWidgetItem(self._get_status_label(account.status)),
                QTableWidgetItem(self._get_auth_status(account)),  # Изменено
                QTableWidgetItem(account.profile_path or f".profiles/{account.name}"),
                None,  # Для комбобокса  
                QTableWidgetItem(self._format_proxy(account.proxy)),  # Форматируем прокси
                QTableWidgetItem(self._get_activity_status(account)),  # Изменено
                QTableWidgetItem(self._get_cookies_status(account))  # Показываем статус куков
            ]
            
            # Устанавливаем элементы
            for col, item in enumerate(items):
                if item is not None:
                    self.table.setItem(row, col + 1, item)
            
            # Устанавливаем комбобокс
            self.table.setCellWidget(row, 5, profile_combo)
        
        self._update_buttons()
    
    def _get_status_label(self, status):
        """Получить метку статуса"""
        labels = {
            "ok": "Готов",
            "cooldown": "Пауза",
            "captcha": "Капча",
            "banned": "Забанен",
            "disabled": "Отключен",
            "error": "Ошибка"
        }
        return labels.get(status, status)
    
    def _get_login_status(self, account):
        """Проверить статус логина"""
        # Проверяем наличие cookies в профиле
        profile_path = Path(account.profile_path)
        cookies_file = profile_path / "Default" / "Cookies"
        
        if cookies_file.exists():
            # Проверяем время последней модификации
            mtime = datetime.fromtimestamp(cookies_file.stat().st_mtime)
            age = datetime.now() - mtime
            
            if age.days < 7:  # Cookies свежие (меньше недели)
                return "✅ Залогинен"
            else:
                return "⚠️ Требует обновления"
        return "❌ Не залогинен"
    
    def _is_logged_in(self, account):
        """Проверить залогинен ли аккаунт"""
        # Всегда возвращаем False чтобы реально проверить через Wordstat
        return False
    
    def _format_timestamp(self, ts):
        """Форматировать временную метку"""
        if ts:
            return ts.strftime("%Y-%m-%d %H:%M")
        return ""
    
    def _get_auth_status(self, account):
        """Получить статус авторизации"""
        # Проверяем куки в выбранном профиле
        profile_path = account.profile_path or f"C:/AI/yandex/.profiles/{account.name}"
        
        # Если используем wordstat_main - проверяем куки там
        if "wordstat_main" in profile_path:
            profile_path = "C:/AI/yandex/.profiles/wordstat_main"
            
        from pathlib import Path
        cookies_file = Path(profile_path) / "Default" / "Cookies"
        
        if cookies_file.exists() and cookies_file.stat().st_size > 1000:
            # Проверяем свежесть куков
            from datetime import datetime
            age_days = (datetime.now().timestamp() - cookies_file.stat().st_mtime) / 86400
            if age_days < 7:
                return "Залогинен"
            else:
                return "Куки устарели"
        
        return "Не залогинен"
    
    def _format_proxy(self, proxy):
        """Форматировать прокси для отображения"""
        if not proxy:
            return "No proxy"
        
        # Извлекаем IP из прокси
        if "@" in str(proxy):
            # Формат: http://user:pass@ip:port
            parts = str(proxy).split("@")
            if len(parts) > 1:
                ip_port = parts[1].replace("http://", "")
                # Показываем только IP и порт
                if ":" in ip_port:
                    ip = ip_port.split(":")[0]
                    # Определяем страну по IP
                    if ip.startswith("213.139"):
                        return f"KZ {ip}"  # KZ вместо флага
                    return ip
        return str(proxy)[:20] + "..."
    
    def _get_activity_status(self, account):
        """Получить статус активности аккаунта"""
        # Проверяем cookies для определения активности
        profile_path = Path(account.profile_path if account.profile_path else f".profiles/{account.name}")
        cookies_file = profile_path / "Default" / "Cookies"
        
        if cookies_file.exists():
            from datetime import datetime
            mtime = datetime.fromtimestamp(cookies_file.stat().st_mtime)
            age = datetime.now() - mtime
            
            if age.total_seconds() < 300:  # 5 минут
                return "Активен сейчас"
            elif age.total_seconds() < 3600:  # 1 час
                return "Активен недавно"
            elif age.days < 1:
                return "Использован сегодня"
            elif age.days < 7:
                return f"{age.days} дн. назад"
            else:
                return "Неактивен"
        else:
            return "Не использован"
    
    def add_account(self):
        """Добавить новый аккаунт"""
        from ..app.main import AccountDialog
        
        dialog = AccountDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    account_service.create_account(**data)
                    self.refresh()
                    self.accounts_changed.emit()
                    QMessageBox.information(self, "Успех", "Аккаунт добавлен")
                except Exception as e:
                    QMessageBox.warning(self, "Ошибка", str(e))
    
    def edit_account(self):
        """Редактировать аккаунт"""
        account = self._current_account()
        if not account:
            return
            
        from ..app.main import AccountDialog
        import json
        from pathlib import Path
        
        # Загружаем данные из accounts.json
        password = ""
        secret_answer = ""
        accounts_file = Path("C:/AI/yandex/configs/accounts.json")
        if accounts_file.exists():
            with open(accounts_file, 'r', encoding='utf-8') as f:
                accounts = json.load(f)
                for acc in accounts:
                    if acc.get("login") == account.name:
                        password = acc.get("password", "")
                        secret_answer = acc.get("secret", "")
                        break
        
        dialog = AccountDialog(self, data={
            "name": account.name,
            "password": password,
            "secret_answer": secret_answer,
            "profile_path": account.profile_path,
            "proxy": account.proxy,
            "notes": account.notes
        })
        
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    account_service.update_account(account.id, **data)
                    self.refresh()
                    self.accounts_changed.emit()
                except Exception as e:
                    QMessageBox.warning(self, "Ошибка", str(e))
    
    def delete_account(self):
        """Удалить аккаунт"""
        account = self._current_account()
        if not account:
            return
            
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить аккаунт '{account.name}'?\n\n"
            f"Это также удалит его из accounts.json\n"
            f"Профиль браузера НЕ будет удален",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Удаляем из базы данных
                account_service.delete_account(account.id)
                
                # Удаляем из accounts.json
                import json
                from pathlib import Path
                
                accounts_file = Path("C:/AI/yandex/configs/accounts.json")
                if accounts_file.exists():
                    with open(accounts_file, 'r', encoding='utf-8') as f:
                        accounts = json.load(f)
                    
                    # Удаляем аккаунт из списка
                    accounts = [acc for acc in accounts if acc.get("login") != account.name]
                    
                    # Сохраняем обратно
                    with open(accounts_file, 'w', encoding='utf-8') as f:
                        json.dump(accounts, f, ensure_ascii=False, indent=2)
                    
                    self.log_action(f"Аккаунт {account.name} удален из accounts.json")
                
                self.refresh()
                self.accounts_changed.emit()
                QMessageBox.information(self, "Успех", f"Аккаунт {account.name} удален")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", str(e))
    
    def import_accounts(self):
        """Импортировать аккаунты из файла"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл с аккаунтами",
            "",
            "Text files (*.txt);;CSV files (*.csv);;All files (*.*)"
        )
        
        if filename:
            try:
                # TODO: Реализовать импорт
                QMessageBox.information(self, "Импорт", "Функция в разработке")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка импорта", str(e))
    
    def login_selected(self):
        """Открыть Chrome с CDP для ручного логина"""
        selected_rows = self._selected_rows()
        if not selected_rows:
            QMessageBox.warning(self, "Внимание", "Выберите аккаунты для логина")
            return
        
        import subprocess
        from pathlib import Path
        import psutil
        
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        
        # Убиваем все процессы Chrome перед запуском
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'chrome.exe' in proc.info['name'].lower():
                    proc.kill()
            except:
                pass
        
        import time
        time.sleep(1)
        
        for row in selected_rows:
            account = self._accounts[row]
            # Берем профиль ИЗ БАЗЫ ДАННЫХ
            profile_path = account.profile_path or f"C:/AI/yandex/.profiles/{account.name}"
            
            # Если путь относительный - делаем полным
            if not profile_path.startswith("C:"):
                profile_path = f"C:/AI/yandex/{profile_path}"
            
            # Используем уникальный порт для каждого аккаунта
            port = 9222 + (hash(account.name) % 100)
            
            # Запускаем Chrome с CDP портом (БЕЗ флагов автоматизации!)
            # Это ОБЫЧНЫЙ Chrome с возможностью подключения через CDP
            subprocess.Popen([
                chrome_path,
                f"--user-data-dir={profile_path}",
                f"--remote-debugging-port={port}",  # Уникальный CDP порт!
                "--no-first-run",
                "--no-default-browser-check",
                "https://wordstat.yandex.ru"
            ])
            
            self.log_action(f"Chrome запущен для {account.name} на порту {port}")
        
        self.log_action(f"Открыто Chrome с CDP для ручного логина: {len(selected_rows)}")
    
    def auto_login_selected(self):
        """Автоматическая авторизация ВЫБРАННЫХ аккаунтов (где стоят галочки)"""
        # Берем только выбранные аккаунты
        selected_rows = self._selected_rows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Внимание", "Выберите аккаунты для автологина (поставьте галочки)")
            return
        
        # Если выбрано больше одного - спрашиваем подтверждение
        if len(selected_rows) > 1:
            reply = QMessageBox.question(self, "Подтверждение",
                f"Будет выполнена авторизация {len(selected_rows)} выбранных аккаунтов.\n\n"
                f"Каждый аккаунт будет открыт в отдельном браузере.\n"
                f"Продолжить?",
                QMessageBox.Yes | QMessageBox.No)
            
            if reply != QMessageBox.Yes:
                return
        
        self.log_action(f"Запуск автологина для {len(selected_rows)} выбранных аккаунтов...")
        
        # Запускаем автологин только для ВЫБРАННЫХ аккаунтов
        self.auto_login_threads = []
        for idx, row_idx in enumerate(selected_rows):
            account = self._accounts[row_idx]
            self.log_action(f"[{idx+1}/{len(selected_rows)}] Запуск автологина для {account.name}...")
            
            # Создаем отдельный поток для каждого аккаунта
            thread = AutoLoginThread(account)
            thread.status_signal.connect(lambda msg, acc=account.name: self.log_action(f"[{acc}] {msg}"))
            thread.progress_signal.connect(self._update_progress)
            thread.secret_question_signal.connect(self._handle_secret_question)
            thread.finished_signal.connect(lambda success, msg, acc=account.name: self._on_auto_login_finished(success, f"[{acc}] {msg}"))
            
            # ВАЖНО: Большая задержка между запусками чтобы не вызвать капчу!
            QTimer.singleShot(idx * 10000, thread.start)  # 10 секунд между запусками!
            self.auto_login_threads.append(thread)
        
        # Отключаем кнопки на время авторизации
        self.auto_login_btn.setEnabled(False)
        self.log_action(f"Запуск автологина для {account.name}...")
    
    def _handle_secret_question(self, account_name: str, question_text: str):
        """Обработка секретного вопроса"""
        from PySide6.QtWidgets import QInputDialog
        
        # Показываем диалог для ввода ответа
        answer, ok = QInputDialog.getText(
            self,
            "Секретный вопрос",
            f"Аккаунт: {account_name}\n\n{question_text}\n\nВведите ответ:",
            echo=QLineEdit.Normal
        )
        
        if ok and answer:
            # Передаем ответ в поток
            if hasattr(self, 'auto_login_thread'):
                self.auto_login_thread.set_secret_answer(answer)
    
    def _update_progress(self, value: int):
        """Обновление прогресса"""
        # Если есть прогресс-бар, обновляем его
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(value)
    
    def _on_auto_login_finished(self, success: bool, message: str):
        """Обработка завершения автологина"""
        # Включаем кнопку обратно
        self.auto_login_btn.setEnabled(True)
        
        if success:
            self.log_action(f"[OK] {message}")
            # Обновляем таблицу
            self.refresh()
        else:
            self.log_action(f"[ERROR] {message}")
            QMessageBox.warning(self, "Ошибка автологина", message)
    
    def launch_browsers_cdp(self):
        """Открыть браузеры для парсинга с CDP портами БЕЗ АВТОЛОГИНА!"""
        import subprocess
        import time
        from pathlib import Path
        
        # ПРАВИЛО №1: НЕ ЛОМАТЬ ТО ЧТО РАБОТАЕТ!
        # Получаем ТОЛЬКО ВЫБРАННЫЕ аккаунты
        selected_rows = self._selected_rows()
        if not selected_rows:
            QMessageBox.warning(self, "Внимание", "Выберите аккаунты для запуска")
            return
        
        # Получаем имена аккаунтов напрямую из списка _accounts
        selected_accounts = []
        for row in selected_rows:
            if row < len(self._accounts):
                account = self._accounts[row]
                selected_accounts.append(account.name)
        
        self.log_action(f"Запуск {len(selected_accounts)} выбранных браузеров для парсинга...")
        
        # ПРАВИЛЬНЫЕ профили из Browser Management
        profile_mapping = {
            "dsmismirnov": "wordstat_main",  # ВАЖНО: wordstat_main!
            "kuznepetya": "kuznepetya",
            "semenovmsemionov": "semenovmsemionov", 
            "vfefyodorov": "vfefyodorov",
            "volkovsvolkow": "volkovsvolkow"
        }
        
        # Спрашиваем подтверждение
        reply = QMessageBox.question(self, "Запуск браузеров",
            f"Будет запущено {len(selected_accounts)} браузеров с CDP портами.\n\n"
            f"Выбранные аккаунты:\n" + "\n".join([f"  • {acc}" for acc in selected_accounts]) + "\n\n"
            f"Браузеры откроются с существующими куками.\n"
            f"НЕ БУДЕТ попыток автологина.\n"
            f"Все существующие Chrome будут закрыты.\n\n"
            f"Продолжить?")
        
        if reply != QMessageBox.Yes:
            return
            
        self.log_action("Закрываю старые Chrome процессы...")
        
        # Убиваем старые Chrome
        subprocess.run(
            ["taskkill", "/F", "/IM", "chrome.exe"], 
            capture_output=True, 
            shell=True
        )
        time.sleep(2)
        
        chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        base_path = Path("C:/AI/yandex/.profiles")
        
        # Запускаем ТОЛЬКО ВЫБРАННЫЕ браузеры
        launched = 0
        port_base = 9222
        
        for i, account_name in enumerate(selected_accounts):
            # Получаем правильный профиль для аккаунта
            if account_name in profile_mapping:
                profile = profile_mapping[account_name]
            else:
                # Если нет в маппинге - используем стандартный путь
                profile = account_name
                
            port = port_base + i
            profile_path = base_path / profile
            
            # Проверяем профиль
            if not profile_path.exists():
                self.log_action(f"[ERROR] Профиль не найден: {profile_path}")
                continue
                
            # Проверяем куки
            cookies_file = profile_path / "Default" / "Network" / "Cookies"
            if cookies_file.exists():
                size_kb = cookies_file.stat().st_size / 1024
                self.log_action(f"[{account_name}] Cookies: {size_kb:.1f}KB")
            else:
                self.log_action(f"[{account_name}] WARNING: Cookies not found!")
            
            # Запускаем Chrome с CDP БЕЗ playwright, БЕЗ автологина!
            cmd = [
                chrome_exe,
                f"--user-data-dir={profile_path}",
                f"--remote-debugging-port={port}",
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "https://wordstat.yandex.ru/?region=225"
            ]
            
            self.log_action(f"[{account_name}] Запуск Chrome на порту {port}...")
            
            try:
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                launched += 1
                self.log_action(f"[{account_name}] ✅ Chrome запущен на порту {port}")
                time.sleep(3)  # Задержка между запусками
            except Exception as e:
                self.log_action(f"[{account_name}] ❌ Ошибка: {e}")
        
        if launched > 0:
            self.log_action(f"\n✅ Запущено {launched} браузеров!")
            # Показываем правильные порты
            ports = [str(9222 + i) for i in range(launched)]
            self.log_action(f"CDP порты: {', '.join(ports)}")
            self.log_action(f"Теперь можно запускать парсер!")
            
            QMessageBox.information(self, "Успех", 
                f"Запущено {launched} браузеров с CDP!\n\n"
                f"Аккаунты: {', '.join(selected_accounts)}\n"
                f"Порты: {', '.join(ports)}\n\n"
                f"Браузеры открыты с существующими куками.\n"
                f"Теперь запустите парсер.")
        else:
            self.log_action("❌ Не удалось запустить браузеры")
            QMessageBox.warning(self, "Ошибка", "Не удалось запустить браузеры")
    
    def login_all(self):
        """Автологин для новых аккаунтов - последовательная авторизация"""
        if not self._accounts:
            QMessageBox.warning(self, "Внимание", "Нет аккаунтов для логина")
            return
        
        self.log_action("Запуск последовательной авторизации всех аккаунтов...")
        
        # Спрашиваем подтверждение
        reply = QMessageBox.question(self, "Подтверждение",
            f"Будет выполнен последовательный вход в {len(self._accounts)} аккаунт(ов).\n\n"
            f"Каждый аккаунт будет авторизован автоматически.\n"
            f"Это может занять несколько минут.\n\n"
            f"Продолжить?")
        
        if reply == QMessageBox.Yes:
            self.log_action("Начинаем последовательную авторизацию...")
            # Запускаем последовательную авторизацию
            self._current_login_index = 0
            self._login_next_account()
    
    def _login_next_account(self):
        """Логин в следующий аккаунт из списка"""
        if self._current_login_index >= len(self._accounts):
            # Все аккаунты обработаны
            self.log_action("✅ Авторизация всех аккаунтов завершена!")
            QMessageBox.information(self, "Готово", "Авторизация всех аккаунтов завершена!")
            self.refresh()
            return
        
        account = self._accounts[self._current_login_index]
        self.log_action(f"Авторизация {self._current_login_index + 1}/{len(self._accounts)}: {account.name}...")
        
        # Запускаем автологин для текущего аккаунта
        self.auto_login_thread = AutoLoginThread(account)
        self.auto_login_thread.status_signal.connect(lambda msg: self.log_action(f"[{account.name}] {msg}"))
        self.auto_login_thread.finished_signal.connect(self._on_account_login_finished)
        self.auto_login_thread.start()
    
    def _on_account_login_finished(self, success: bool, message: str):
        """Обработка завершения логина одного аккаунта"""
        account = self._accounts[self._current_login_index]
        
        if success:
            self.log_action(f"✅ {account.name}: {message}")
        else:
            self.log_action(f"❌ {account.name}: {message}")
        
        # Переходим к следующему аккаунту
        self._current_login_index += 1
        
        # Небольшая задержка перед следующим аккаунтом
        QTimer.singleShot(2000, self._login_next_account)
    
    def _start_login(self, accounts, headless=False, visual_mode=False):
        """Запустить процесс логина"""
        if self.login_thread and self.login_thread.isRunning():
            QMessageBox.warning(self, "Внимание", "Процесс логина уже запущен")
            return
        
        # Блокируем кнопки
        self.login_btn.setEnabled(False)
        self.login_all_btn.setEnabled(False)
        
        # Показываем прогресс
        self.login_progress.setVisible(True)
        self.login_progress.setRange(0, 0)  # Неопределенный прогресс
        
        # Создаем и запускаем поток
        # visual_mode=True для визуального парсинга
        self.login_thread = LoginWorkerThread(accounts, check_only=headless, visual_mode=visual_mode)
        self.login_thread.progress_signal.connect(self.on_login_progress)
        self.login_thread.account_logged_signal.connect(self.on_account_logged)
        self.login_thread.finished_signal.connect(self.on_login_finished)
        self.login_thread.start()
        
        self.login_status_label.setText(f"Запуск {len(accounts)} браузеров...")
    
    def on_login_progress(self, message):
        """Обработка прогресса логина"""
        self.login_status_label.setText(message)
    
    def on_account_logged(self, account_id, success, message):
        """Обработка логина конкретного аккаунта"""
        # Обновляем статус в БД
        if success:
            account_service.mark_ok(account_id)
        
        # Обновляем таблицу
        self.refresh()
    
    def on_login_finished(self, success, message):
        """Обработка завершения логина"""
        self.login_progress.setVisible(False)
        self.login_btn.setEnabled(True)
        self.login_all_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Успех", message)
        else:
            QMessageBox.warning(self, "Внимание", message)
        
        self.login_status_label.setText("Готов к работе")
        self.refresh()
    
    def open_browsers_for_login(self):
        """Открыть браузеры только для тех аккаунтов где нужен логин"""
        from pathlib import Path
        
        # Фильтруем аккаунты которые требуют логина
        accounts_to_check = []
        for acc in self._accounts:
            if acc.name != "demo_account":  # Пропускаем демо
                # Используем полный путь к профилю
                # acc.profile_path может содержать относительный путь типа ".profiles/dsmismirnov"
                if acc.profile_path:
                    # Если путь начинается с .profiles - это относительный путь
                    if acc.profile_path.startswith(".profiles"):
                        profile_full_path = Path("C:/AI/yandex") / acc.profile_path
                    else:
                        profile_full_path = Path(acc.profile_path)
                else:
                    # Если путь не задан, используем стандартный
                    profile_full_path = Path("C:/AI/yandex/.profiles") / acc.name
                
                # Проверяем есть ли сохраненные куки
                cookie_file = profile_full_path / "Default" / "Cookies"
                
                # Добавляем в список для проверки
                accounts_to_check.append({
                    "account": acc,
                    "has_cookies": cookie_file.exists(),
                    "profile_path": str(profile_full_path)
                })
        
        if not accounts_to_check:
            QMessageBox.information(self, "Информация", "Нет аккаунтов для проверки")
            return
        
        # Показываем диалог выбора
        msg = "Статус аккаунтов:\n\n"
        
        # Даже если все авторизованы, открываем браузеры для визуального парсинга
        msg += "\n⚠️ ВНИМАНИЕ: Браузеры будут открыты для визуального парсинга.\n"
        msg += "Все аккаунты должны быть авторизованы.\n"
        msg += "Открыть браузеры?"
        
        reply = QMessageBox.question(self, "Открыть браузеры для логина", msg)
        if reply == QMessageBox.Yes:
            # Запускаем браузеры для всех аккаунтов для визуального парсинга
            # Извлекаем объекты аккаунтов из словарей
            all_accounts = [item["account"] for item in accounts_to_check]
            self._start_login(all_accounts, visual_mode=True)
    
    def show_browser_status(self):
        """Показать статус браузеров"""
        if hasattr(self, 'browser_manager') and self.browser_manager:
            self.browser_manager.show_status()
        else:
            QMessageBox.information(self, "Статус", "Браузеры не запущены")
    
    def update_browser_status(self):
        """Обновить статусы залогинены ли браузеры"""
        if hasattr(self, 'browser_manager') and self.browser_manager:
            QMessageBox.information(self, "Статус", "Проверка статусов...")
            # TODO: реализовать проверку через browser_manager
        else:
            QMessageBox.warning(self, "Внимание", "Браузеры не запущены")
    
    def minimize_all_browsers(self):
        """Минимизировать все браузеры"""
        if hasattr(self, 'browser_manager') and self.browser_manager:
            try:
                # TODO: реализовать минимизацию в browser_manager
                QMessageBox.information(self, "Готово", "Функция в разработке")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", str(e))
        else:
            QMessageBox.warning(self, "Внимание", "Браузеры не запущены")
    
    def close_all_browsers(self):
        """Закрыть все браузеры"""
        if hasattr(self, 'browser_manager') and self.browser_manager:
            reply = QMessageBox.question(self, "Подтверждение",
                "Закрыть все браузеры?",
                QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.browser_manager.close_all())
                    self.browser_manager = None
                    QMessageBox.information(self, "Готово", "Браузеры закрыты")
                except Exception as e:
                    QMessageBox.warning(self, "Ошибка", f"Ошибка при закрытии: {e}")
        else:
            QMessageBox.information(self, "Информация", "Браузеры не запущены")
    
    def on_table_double_click(self, item):
        """Обработчик двойного клика по ячейке таблицы"""
        column = self.table.currentColumn()
        
        # Если клик по колонке "Куки" (индекс 7)
        if column == 7:
            self.edit_cookies()
        else:
            self.edit_account()
    
    def edit_cookies(self):
        """Редактировать куки для аккаунта"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox, QLabel
        
        # Путь к профилю wordstat_main
        profile_path = Path("C:/AI/yandex/.profiles/wordstat_main")
        
        # Создаем диалог
        dialog = QDialog(self)
        dialog.setWindowTitle("Управление куками Wordstat")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Информация
        info = QLabel("""
<b>Важные куки для Wordstat:</b><br>
• sessionid2 - основная сессия<br>
• yandex_login - логин пользователя<br>
• yandexuid - ID пользователя<br>
• L - токен авторизации<br>
<br>
<b>Профиль:</b> wordstat_main<br>
<b>Путь:</b> C:\\AI\\yandex\\.profiles\\wordstat_main\\
        """)
        layout.addWidget(info)
        
        # Поле для ввода куков
        cookies_edit = QTextEdit()
        cookies_edit.setPlaceholderText(
            "Вставьте куки в формате:\n"
            "sessionid2=value1; yandex_login=value2; L=value3"
        )
        
        # Пытаемся прочитать текущие куки (упрощенно)
        cookies_file = profile_path / "Default" / "Cookies"
        if cookies_file.exists():
            cookies_edit.setPlainText(f"Файл куков существует: {cookies_file}\nРазмер: {cookies_file.stat().st_size} bytes\n\n[Для редактирования куков используйте браузер]")
        
        layout.addWidget(cookies_edit)
        
        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            # Здесь можно добавить логику сохранения куков
            # Но безопаснее логиниться через браузер
            QMessageBox.information(self, "Информация", 
                "Для изменения куков откройте браузер с профилем wordstat_main\n"
                "и войдите в Яндекс вручную или используйте кнопку 'Автологин'")
    
    def _update_profile(self, account_id, profile_text):
        """Обновить профиль для аккаунта"""
        # Извлекаем имя профиля из текста
        if "wordstat_main" in profile_text:
            profile_name = "wordstat_main"
        elif "(личный)" in profile_text:
            profile_name = profile_text.split(" ")[0]
        else:
            profile_name = profile_text
            
        # Обновляем профиль в базе данных
        profile_path = f"C:/AI/yandex/.profiles/{profile_name}"
        account_service.update_account(account_id, profile_path=profile_path)
        print(f"[Accounts] Профиль для аккаунта {account_id} изменен на {profile_name}")
        
    def on_table_double_click(self, row, col):
        """Обработка двойного клика по таблице"""
        # Если кликнули по колонке куков - открываем диалог редактирования
        if col == 8:  # Колонка куков
            self.edit_cookies(row)
            
    def edit_cookies(self, row):
        """Редактировать куки для аккаунта"""
        account = self._accounts[row]
        profile_path = account.profile_path or f"C:/AI/yandex/.profiles/{account.name}"
        
        # Если путь относительный - делаем полный
        if not profile_path.startswith("C:"):
            profile_path = f"C:/AI/yandex/{profile_path}"
            
        from pathlib import Path
        cookies_file = Path(profile_path) / "Default" / "Cookies"
        
        # Создаем диалог для отображения информации о куках
        msg = QMessageBox(self)
        msg.setWindowTitle(f"Куки для {account.name}")
        msg.setIcon(QMessageBox.Information)
        
        text = f"""
Профиль: {profile_path.split('/')[-1]}
Путь к куками: {cookies_file}

"""
        
        if cookies_file.exists():
            stat = cookies_file.stat()
            size_kb = stat.st_size / 1024
            from datetime import datetime
            age_days = (datetime.now().timestamp() - stat.st_mtime) / 86400
            
            text += f"""Размер файла: {size_kb:.1f} KB
Последнее изменение: {int(age_days)} дней назад

Важные куки для Wordstat:
• sessionid2 - Основная сессия
• yandex_login - Логин пользователя  
• yandexuid - ID пользователя
• L - Токен авторизации
"""
        else:
            text += "Файл куков не найден!\n\nЧтобы добавить куки:\n1. Откройте Chrome с этим профилем\n2. Войдите в Яндекс\n3. Куки сохранятся автоматически"
            
        msg.setText(text)
        msg.exec()
            
    def open_chrome_with_profile(self):
        """Открыть Chrome с профилем выбранного аккаунта"""
        import subprocess
        
        selected = self._selected_rows()
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выберите аккаунт для открытия Chrome")
            return
            
        if len(selected) > 1:
            QMessageBox.warning(self, "Внимание", "Выберите только один аккаунт")
            return
            
        account = self._accounts[selected[0]]
        
        # Определяем профиль
        profile_path = account.profile_path or f"C:/AI/yandex/.profiles/{account.name}"
        
        # Если путь относительный - делаем полный
        if not profile_path.startswith("C:"):
            profile_path = f"C:/AI/yandex/{profile_path}"
            
        # Запускаем Chrome
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        
        try:
            subprocess.Popen([
                chrome_path,
                f"--user-data-dir={profile_path}",
                "--new-window",
                "https://wordstat.yandex.ru"
            ])
            
            self.log_action(f"Chrome запущен с профилем: {profile_path.split('/')[-1]}")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить Chrome: {str(e)}")
        
    def _get_cookies_status(self, account):
        """Получить статус куков для аккаунта"""
        # Определяем профиль из пути аккаунта
        profile_path = account.profile_path or f"C:/AI/yandex/.profiles/{account.name}"
        
        # Конвертируем в Path объект
        if not isinstance(profile_path, Path):
            profile_path = Path(profile_path)
            
        # Проверяем наличие файла куков
        cookies_paths = [
            profile_path / "Default" / "Cookies",
            profile_path / "Default" / "Network" / "Cookies",
            profile_path / "Cookies"
        ]
        
        # Проверяем наличие куков
        for cookie_path in cookies_paths:
            if cookie_path.exists():
                stat = cookie_path.stat()
                if stat.st_size > 1000:  # Файл не пустой
                    # Проверяем свежесть
                    age_days = (datetime.now().timestamp() - stat.st_mtime) / 86400
                    
                    # Формируем статус
                    if age_days < 1:
                        status = "Fresh"
                    elif age_days < 7:
                        status = f"{int(age_days)}d old"
                    else:
                        status = "Expired"
                        
                    # Показываем размер файла для информации
                    size_kb = stat.st_size / 1024
                    return f"{status} ({size_kb:.1f}KB)"
        
        return "No cookies"

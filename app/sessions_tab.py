"""
UI вкладка для управления браузерными сессиями
"""
from __future__ import annotations

import asyncio
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..services import sessions as session_service


class SessionCreationThread(QThread):
    """Поток для создания сессии (ручной логин)"""
    
    log_message = Signal(str)
    completed = Signal(bool, str)
    
    def __init__(self, account_id: int, proxy: Optional[str]) -> None:
        super().__init__()
        self.account_id = account_id
        self.proxy = proxy
    
    def run(self) -> None:
        self.log_message.emit(f"Открываю браузер для логина (аккаунт #{self.account_id})...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            profile_path = loop.run_until_complete(self._run_async())
        except Exception as exc:
            self.log_message.emit(f"✗ Ошибка: {exc}")
            self.log_message.emit(traceback.format_exc())
            self.completed.emit(False, str(exc))
        else:
            self.log_message.emit(f"✓ Сессия создана: {profile_path}")
            self.completed.emit(True, f"Сессия сохранена в {profile_path}")
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()

    async def _run_async(self) -> str:
        return await session_service.create_session_for_account(
            self.account_id,
            self.proxy
        )


class SessionCheckThread(QThread):
    """Поток для проверки статуса сессии"""
    
    completed = Signal(dict)
    
    def __init__(self, profile_path: str) -> None:
        super().__init__()
        self.profile_path = profile_path
    
    def run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                session_service.check_session_status(self.profile_path)
            )
        except Exception as exc:
            self.completed.emit({"error": str(exc), "traceback": traceback.format_exc()})
        else:
            self.completed.emit(result)
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()


class SessionsTab(QWidget):
    """Вкладка управления сессиями в UI"""
    
    sessions_changed = Signal()
    
    def __init__(self, log_widget=None) -> None:
        super().__init__()
        self.log_widget = log_widget
        self._sessions: list[dict] = []
        self._worker: Optional[QThread] = None
        
        # Таблица
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Аккаунт",
            "Статус сессии",
            "Статус аккаунта",
            "Профиль",
            "Последнее использование",
            "Прокси"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        
        # Кнопки
        self.create_btn = QPushButton("Создать сессию")
        self.create_btn.clicked.connect(self.create_session)
        
        self.check_btn = QPushButton("Проверить")
        self.check_btn.clicked.connect(self.check_session)
        
        self.delete_btn = QPushButton("Удалить сессию")
        self.delete_btn.clicked.connect(self.delete_session)
        
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.refresh)
        
        self.open_folder_btn = QPushButton("Открыть папку")
        self.open_folder_btn.clicked.connect(self.open_profile_folder)
        
        buttons = QHBoxLayout()
        buttons.addWidget(self.create_btn)
        buttons.addWidget(self.check_btn)
        buttons.addWidget(self.delete_btn)
        buttons.addWidget(self.open_folder_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.refresh_btn)
        
        # Информация
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setText(
            "💡 Сессии - это сохранённые авторизации в Яндексе.\n"
            "Создайте сессию один раз, потом парсинг будет работать БЕЗ повторного логина!"
        )
        
        # Компоновка
        layout = QVBoxLayout(self)
        layout.addWidget(self.info_label)
        layout.addLayout(buttons)
        layout.addWidget(self.table)
        
        self.refresh()
    
    def _log(self, message: str) -> None:
        if self.log_widget:
            stamp = datetime.now().strftime("%H:%M:%S")
            self.log_widget.append(f"[{stamp}] {message}")
    
    def _selected_session(self) -> Optional[dict]:
        selection = self.table.selectionModel()
        if not selection:
            return None
        indexes = selection.selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        if row < 0 or row >= len(self._sessions):
            return None
        return self._sessions[row]
    
    def _update_buttons(self) -> None:
        session = self._selected_session()
        has_selection = session is not None
        has_session = session and session.get('session_exists')
        
        self.create_btn.setEnabled(has_selection)
        self.check_btn.setEnabled(has_session)
        self.delete_btn.setEnabled(has_session)
        self.open_folder_btn.setEnabled(has_session)
    
    def refresh(self) -> None:
        self._sessions = session_service.list_sessions()
        self.table.setRowCount(len(self._sessions))
        
        for row, session in enumerate(self._sessions):
            session_status = "✓ Есть" if session['session_exists'] else "✗ Нет"
            last_used = self._format_ts(session.get('last_used'))
            
            items = [
                QTableWidgetItem(session['account_name']),
                QTableWidgetItem(session_status),
                QTableWidgetItem(session['status'] or ''),
                QTableWidgetItem(session['profile_path'] or ''),
                QTableWidgetItem(last_used),
                QTableWidgetItem(session['proxy'] or ''),
            ]
            
            items[0].setData(Qt.UserRole, session['account_id'])
            
            for col, item in enumerate(items):
                if col in (0, 1, 2, 4):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
        
        self._update_buttons()
    
    def _format_ts(self, value: Optional[datetime]) -> str:
        if not value:
            return ""
        return value.strftime("%Y-%m-%d %H:%M")
    
    def create_session(self) -> None:
        session = self._selected_session()
        if not session:
            QMessageBox.warning(self, "Выбор аккаунта", "Выберите аккаунт из списка")
            return
        
        reply = QMessageBox.question(
            self,
            "Создание сессии",
            f"Открыть браузер для логина аккаунта '{session['account_name']}'?\n\n"
            "У вас будет 3 минуты чтобы залогиниться.\n"
            "После логина сессия сохранится и парсинг будет работать автоматически.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self._log(f"Создание сессии для {session['account_name']}...")
        self.create_btn.setEnabled(False)
        
        self._worker = SessionCreationThread(
            session['account_id'],
            session['proxy']
        )
        self._worker.log_message.connect(self._log)
        self._worker.completed.connect(self._on_creation_completed)
        self._worker.start()
    
    def _on_creation_completed(self, success: bool, message: str) -> None:
        self.create_btn.setEnabled(True)
        self._worker = None
        
        if success:
            QMessageBox.information(self, "Успех", message)
        else:
            QMessageBox.warning(self, "Ошибка", message)
        
        self.refresh()
        self.sessions_changed.emit()
    
    def check_session(self) -> None:
        session = self._selected_session()
        if not session or not session.get('profile_path'):
            return
        
        self._log(f"Проверка сессии {session['account_name']}...")
        self.check_btn.setEnabled(False)
        
        self._worker = SessionCheckThread(session['profile_path'])
        self._worker.completed.connect(self._on_check_completed)
        self._worker.start()
    
    def _on_check_completed(self, result: dict) -> None:
        self.check_btn.setEnabled(True)
        self._worker = None
        
        active = result.get('active', False)
        message = result.get('message', '')
        
        if active:
            QMessageBox.information(self, "Проверка сессии", f"✓ {message}")
        else:
            QMessageBox.warning(self, "Проверка сессии", f"✗ {message}\n\nСоздайте сессию заново.")
    
    def delete_session(self) -> None:
        session = self._selected_session()
        if not session:
            return
        
        reply = QMessageBox.question(
            self,
            "Удаление сессии",
            f"Удалить сохранённую сессию для '{session['account_name']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            session_service.delete_session(session['account_id'])
            self._log(f"Сессия удалена: {session['account_name']}")
            self.refresh()
            self.sessions_changed.emit()
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
    
    def open_profile_folder(self) -> None:
        session = self._selected_session()
        if not session or not session.get('profile_path'):
            return
        
        profile_path = Path(session['profile_path'])
        if not profile_path.exists():
            QMessageBox.warning(self, "Папка не найдена", f"{profile_path}")
            return
        
        import subprocess
        import sys
        
        if sys.platform == 'win32':
            subprocess.run(['explorer', str(profile_path)])
        elif sys.platform == 'darwin':
            subprocess.run(['open', str(profile_path)])
        else:
            subprocess.run(['xdg-open', str(profile_path)])

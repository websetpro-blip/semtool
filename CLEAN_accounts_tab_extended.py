"""
Расширенная вкладка управления аккаунтами с функцией логина

ПРАВИЛО №1: НЕ ЛОМАТЬ ТО ЧТО РАБОТАЕТ!
- Не удалять рабочие функции
- Не изменять работающую логику
- Не трогать то, что пользователь не просил менять
"""

import asyncio
import threading
import traceback
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
from ..services.accounts import test_proxy, get_cookies_status, autologin_account
from ..services.captcha import CaptchaService
from ..workers.visual_browser_manager import VisualBrowserManager, BrowserStatus
# Old worker no longer used, now using CDP approach


class AutoLoginThread(QThread):
    """Thread for automatic account authorization"""
    status_signal = Signal(str)  # Operation status
    progress_signal = Signal(int)  # Progress 0-100
    secret_question_signal = Signal(str, str)  # account_name, question_text
    finished_signal = Signal(bool, str)  # success, message
    
    def __init__(self, account, parent=None):
        super().__init__(parent)
        self.account = account
        self.secret_answer = None
        
    def set_secret_answer(self, answer):
        """Set secret question answer"""
        self.secret_answer = answer
        
    def run(self):
        """Start smart autologin based on GPT solution"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_async())
        except Exception as exc:
            self.status_signal.emit(f"[ERROR] {exc}")
            self.status_signal.emit(traceback.format_exc())
            self.finished_signal.emit(False, str(exc))
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()

    async def _run_async(self):
        from ..workers.yandex_smart_login import YandexSmartLogin
        import json
        from pathlib import Path

        profile_path = self.account.profile_path

        # CHECK: Profile MUST be from DB!
        if not profile_path:
            self.status_signal.emit(f"[ERROR] Account {self.account.name} has NO profile_path in DB!")
            self.finished_signal.emit(False, "Profile not specified in DB")
            return

        self.status_signal.emit(f"[OK] Profile from DB: {profile_path}")

        if not profile_path.startswith("C:"):
            profile_path = f"C:/AI/yandex/{profile_path}"
            self.status_signal.emit(f"[INFO] Path converted: {profile_path}")

        accounts_file = Path("C:/AI/yandex/configs/accounts.json")
        if not accounts_file.exists():
            self.status_signal.emit(f"[ERROR] File accounts.json not found!")
            self.finished_signal.emit(False, "File accounts.json not found")
            return

        with open(accounts_file, 'r', encoding='utf-8') as f:
            accounts_data = json.load(f)
            account_info = None
            for acc in accounts_data:
                if acc["login"] == self.account.name:
                    account_info = acc
                    break

        if not account_info:
            self.status_signal.emit(f"[ERROR] Account {self.account.name} not found in accounts.json!")
            self.finished_signal.emit(False, f"Account not found in accounts.json")
            return

        self.status_signal.emit(f"[CDP] Starting autologin for {self.account.name}...")

        secret_answer = self.secret_answer
        if not secret_answer and "secret" in account_info and account_info["secret"]:
            secret_answer = account_info["secret"]
            self.status_signal.emit(f"[CDP] Found saved secret question answer")

        port = 9222 + (hash(self.account.name) % 100)
        self.status_signal.emit(f"[CDP] Using port {port} for {self.account.name}")

        smart_login = YandexSmartLogin()
        smart_login.status_update.connect(self.status_signal.emit)
        smart_login.progress_update.connect(self.progress_signal.emit)
        smart_login.secret_question_required.connect(self.secret_question_signal.emit)

        if secret_answer:
            smart_login.set_secret_answer(secret_answer)

        proxy_to_use = account_info.get("proxy", None)
        if proxy_to_use:
            self.status_signal.emit(f"[INFO] Using proxy: {proxy_to_use.split('@')[0]}@***")

        self.status_signal.emit(f"[SMART] Starting autologin...")
        success = await smart_login.login(
            account_name=self.account.name,
            profile_path=profile_path,
            proxy=proxy_to_use
        )

        if success:
            self.status_signal.emit(f"[OK] Autologin successful for {self.account.name}!")
            self.finished_signal.emit(True, "Authorization successful")
        else:
            self.status_signal.emit(f"[ERROR] Autologin failed for {self.account.name}")
            self.finished_signal.emit(False, "Authorization error")

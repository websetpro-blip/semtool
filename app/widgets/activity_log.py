# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QTextCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


class ActivityLogWidget(QWidget):
    """
    Журнал активности внизу окна, повторяет логику Key Collector:
    заголовок + текстовое поле + кнопки управления (очистка/копия/сохранение/пауза).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._autoscroll_enabled = True
        self._build_ui()

    # ------------------------------------------------------------------ public
    def append_line(self, message: str, *, with_timestamp: bool = True) -> None:
        """Добавить запись в журнал."""
        if with_timestamp:
            stamp = datetime.now().strftime("%H:%M:%S")
            text = f"[{stamp}] {message}"
        else:
            text = message

        self._log.appendPlainText(text)
        if self._autoscroll_enabled:
            cursor = self._log.textCursor()
            cursor.movePosition(QTextCursor.End)
            self._log.setTextCursor(cursor)

    def clear(self) -> None:
        self._log.clear()

    # ----------------------------------------------------------------- actions
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(6)

        title = QLabel("Журнал активности")
        title.setObjectName("activityLogLabel")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(title)

        self._log = QPlainTextEdit(readOnly=True)
        self._log.setObjectName("activityLogView")
        layout.addWidget(self._log, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)

        self._btn_clear = QPushButton("Очистить")
        self._btn_clear.clicked.connect(self.clear)
        buttons.addWidget(self._btn_clear)

        btn_copy = QPushButton("Копировать всё")
        btn_copy.clicked.connect(self._copy_all)
        buttons.addWidget(btn_copy)

        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self._save_to_file)
        buttons.addWidget(btn_save)

        self._btn_autoscroll = QPushButton("Пауза автоскролла")
        self._btn_autoscroll.setCheckable(True)
        self._btn_autoscroll.toggled.connect(self._toggle_autoscroll)
        buttons.addWidget(self._btn_autoscroll)

        buttons.addStretch()
        layout.addLayout(buttons)

    def _copy_all(self) -> None:
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self._log.toPlainText())

    def _save_to_file(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить журнал",
            str(Path.home() / "keyset_activity_log.txt"),
            "Text files (*.txt);;All files (*.*)",
        )
        if not filename:
            return
        Path(filename).write_text(self._log.toPlainText(), encoding="utf-8")

    def _toggle_autoscroll(self, checked: bool) -> None:
        self._autoscroll_enabled = not checked
        self._btn_autoscroll.setText("Возобновить автоскролл" if checked else "Пауза автоскролла")


__all__ = ["ActivityLogWidget"]

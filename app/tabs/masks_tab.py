# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import defaultdict

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QLineEdit,
)


class MasksTab(QWidget):
    """
    Вкладка для подготовки масок перед парсингом.
    Даёт быстрые операции нормализации, пересечений и отправки в основной парсер.
    """

    def __init__(self, parent=None, send_to_parsing_callback=None) -> None:
        super().__init__(parent)
        self._send = send_to_parsing_callback

        self._source = QTextEdit(placeholderText="Исходные маски (по одной на строке)…")
        self._result = QTextEdit(readOnly=True)
        self._stopwords = QLineEdit(placeholderText="Стоп-слова, через запятую")

        btn_normalize = QPushButton("Нормализовать")
        btn_normalize.clicked.connect(self._normalize)

        btn_cross = QPushButton("Пересечения (черновик)")
        btn_cross.clicked.connect(self._intersect)

        btn_send = QPushButton("Перенести в Парсинг")
        btn_send.clicked.connect(self._send_to_parsing)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Исходные маски"))
        layout.addWidget(self._source, 1)
        layout.addWidget(self._stopwords)

        buttons = QHBoxLayout()
        buttons.addWidget(btn_normalize)
        buttons.addWidget(btn_cross)
        buttons.addWidget(btn_send)
        layout.addLayout(buttons)

        layout.addWidget(QLabel("Результат"))
        layout.addWidget(self._result, 1)

    # ------------------------------------------------------------------ actions
    def _normalize(self) -> None:
        stopwords = {
            token.strip().lower()
            for token in (self._stopwords.text() or "").split(",")
            if token.strip()
        }
        lines = [
            line.strip().lower()
            for line in self._source.toPlainText().splitlines()
            if line.strip()
        ]
        cleaned = []
        for line in lines:
            tokens = [token for token in line.split() if token not in stopwords]
            if tokens:
                cleaned.append(" ".join(tokens))
        self._result.setPlainText("\n".join(sorted(set(cleaned))))

    def _intersect(self) -> None:
        groups = defaultdict(list)
        block_index = 0
        for block in self._source.toPlainText().split("\n\n"):
            block = block.strip()
            if not block:
                continue
            key = f"Блок {block_index + 1}"
            block_index += 1
            for token in block.split(","):
                token = token.strip()
                if token:
                    groups[key].append(token)

        if len(groups) < 2:
            # Фолбэк — просто отсортированные уникальные строки
            phrases = sorted(
                {
                    line.strip()
                    for line in self._source.toPlainText().splitlines()
                    if line.strip()
                }
            )
        else:
            blocks = list(groups.values())
            phrases = set()
            prefix = blocks[0]
            suffix = blocks[1]
            for left in prefix:
                for right in suffix:
                    phrases.add(f"{left} {right}")
            phrases = sorted(phrases)
        self._result.setPlainText("\n".join(phrases))

    def _send_to_parsing(self) -> None:
        if not callable(self._send):
            QMessageBox.information(self, "Готово", "Подключи send_to_parsing_callback")
            return
        payload = [
            line.strip()
            for line in self._result.toPlainText().splitlines()
            if line.strip()
        ]
        if payload:
            self._send(payload)


__all__ = ["MasksTab"]


# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)


class GeoDialog(QDialog):
    """Modal dialog with a searchable region tree."""

    def __init__(self, regions_json: str | Path = "data/regions_tree.json", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Выбор регионов")
        self.resize(520, 620)

        self._search = QLineEdit(placeholderText="Поиск по регионам…")
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self._search)
        layout.addWidget(self._tree, 1)
        layout.addWidget(buttons)

        self._load_regions(regions_json)
        self._search.textChanged.connect(self._filter_tree)

    def _load_regions(self, path: str | Path) -> None:
        dataset = Path(path)
        try:
            data = json.loads(dataset.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self._tree.clear()
            return

        self._tree.clear()
        for entry in data:
            top = QTreeWidgetItem([f"{entry['name']} ({entry['id']})"])
            top.setCheckState(0, Qt.Unchecked)
            for child in entry.get("children", []):
                sub = QTreeWidgetItem([f"{child['name']} ({child['id']})"])
                sub.setCheckState(0, Qt.Unchecked)
                top.addChild(sub)
            self._tree.addTopLevelItem(top)
        self._tree.expandAll()

    def _filter_tree(self, text: str) -> None:
        pattern = (text or "").lower()
        root = self._tree.invisibleRootItem()
        for index in range(root.childCount()):
            self._filter_branch(root.child(index), pattern)

    def _filter_branch(self, node: QTreeWidgetItem, pattern: str) -> bool:
        visible = pattern in node.text(0).lower()
        for index in range(node.childCount()):
            if self._filter_branch(node.child(index), pattern):
                visible = True
        node.setHidden(not visible)
        return visible

    def selected_region_ids(self) -> list[int]:
        """Return checked region ids or Russian default."""

        def collect(item: QTreeWidgetItem) -> list[int]:
            values: list[int] = []
            if item.checkState(0) == Qt.Checked:
                label = item.text(0)
                if "(" in label and ")" in label:
                    try:
                        values.append(int(label.split("(")[1].split(")")[0]))
                    except ValueError:
                        pass
            for idx in range(item.childCount()):
                values.extend(collect(item.child(idx)))
            return values

        root = self._tree.invisibleRootItem()
        result: list[int] = []
        for index in range(root.childCount()):
            result.extend(collect(root.child(index)))
        return result or [225]


__all__ = ["GeoDialog"]


# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import os
from pathlib import Path

from PySide6.QtWidgets import QTableWidget


def export_csv(table: QTableWidget, path: str | os.PathLike) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=";")
        headers = [
            table.horizontalHeaderItem(col).text()
            for col in range(table.columnCount())
        ]
        writer.writerow(headers)
        for row in range(table.rowCount()):
            writer.writerow(
                [
                    table.item(row, col).text() if table.item(row, col) else ""
                    for col in range(table.columnCount())
                ]
            )


__all__ = ["export_csv"]


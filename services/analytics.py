# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem


def _val(item: QTableWidgetItem | None) -> float:
    try:
        text = (item.text() if item else "").replace(",", ".")
        return float(text)
    except (ValueError, AttributeError):
        return 0.0


def enrich_metrics(table: QTableWidget, default_cr: float = 3.0) -> None:
    """Calculate CTR/CPA/Cost metrics inline."""
    for row in range(table.rowCount()):
        shows = _val(table.item(row, 4))
        clicks = _val(table.item(row, 5))
        cpc = _val(table.item(row, 7))
        cost = _val(table.item(row, 9))
        cr_item = table.item(row, 11)
        cr = _val(cr_item) or default_cr

        if not cost:
            cost = clicks * cpc
        ctr = (clicks / shows * 100.0) if shows else 0.0
        conversions = clicks * (cr / 100.0)
        cpa = (cost / conversions) if conversions else 0.0

        table.setItem(row, 6, QTableWidgetItem(f"{ctr:.2f}"))
        table.setItem(row, 9, QTableWidgetItem(f"{cost:.2f}"))
        table.setItem(row, 10, QTableWidgetItem(f"{cpa:.2f}"))
        if cr_item is None or not cr_item.text().strip():
            table.setItem(row, 11, QTableWidgetItem(f"{default_cr:.2f}"))


__all__ = ["enrich_metrics"]


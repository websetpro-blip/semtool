# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QAction, QComboBox, QMenu, QToolBar, QToolButton, QWidgetAction


class ToolbarSignals(QObject):
    """Signal helper so that the toolbar stays dumb."""

    run_freq = Signal()
    run_depth_left = Signal()
    run_depth_right = Signal()
    run_forecast = Signal()
    open_geo = Signal()
    run_minus = Signal()
    run_stopwords = Signal()
    run_export = Signal()
    open_analytics = Signal()
    profile_changed = Signal(str)


class MainToolbar(QToolBar):
    """Key Collector‑style command toolbar for the parsing tab."""

    def __init__(self, parent=None) -> None:
        super().__init__("Сбор данных", parent)
        self.setMovable(False)
        self.sig = ToolbarSignals()
        self._build()

    def _build(self) -> None:
        self.act_freq = QAction("Частотка", self)
        self.act_freq.triggered.connect(self.sig.run_freq)

        menu_depth = QMenu("Вглубь", self)
        act_left = QAction("Левая колонка", self)
        act_left.triggered.connect(self.sig.run_depth_left)
        act_right = QAction("Правая колонка", self)
        act_right.triggered.connect(self.sig.run_depth_right)
        menu_depth.addActions([act_left, act_right])

        btn_depth = QToolButton()
        btn_depth.setText("Вглубь")
        btn_depth.setMenu(menu_depth)
        btn_depth.setPopupMode(QToolButton.MenuButtonPopup)

        self.act_forecast = QAction("Прогноз бюджета", self)
        self.act_forecast.triggered.connect(self.sig.run_forecast)

        self.act_geo = QAction("Гео (дерево)", self)
        self.act_geo.triggered.connect(self.sig.open_geo)

        self.cmb_profile = QComboBox()
        self.cmb_profile.setFixedWidth(220)
        self.cmb_profile.currentTextChanged.connect(self.sig.profile_changed.emit)

        profile_widget = QWidgetAction(self)
        profile_widget.setDefaultWidget(self.cmb_profile)

        self.act_minus = QAction("Минусовка", self)
        self.act_minus.triggered.connect(self.sig.run_minus)

        self.act_stop = QAction("Стоп-слова", self)
        self.act_stop.triggered.connect(self.sig.run_stopwords)

        self.act_export = QAction("Экспорт CSV", self)
        self.act_export.triggered.connect(self.sig.run_export)

        self.act_stats = QAction("Аналитика", self)
        self.act_stats.triggered.connect(self.sig.open_analytics)

        self.addAction(self.act_freq)
        self.addWidget(btn_depth)
        self.addAction(self.act_forecast)
        self.addSeparator()
        self.addAction(self.act_geo)
        self.addAction(profile_widget)
        self.addSeparator()
        self.addAction(self.act_minus)
        self.addAction(self.act_stop)
        self.addAction(self.act_export)
        self.addAction(self.act_stats)

    def set_profiles(self, profiles: list[str]) -> None:
        self.cmb_profile.blockSignals(True)
        self.cmb_profile.clear()
        if profiles:
            self.cmb_profile.addItems(profiles)
        else:
            self.cmb_profile.addItem("Текущий")
        self.cmb_profile.blockSignals(False)


__all__ = ["MainToolbar", "ToolbarSignals"]


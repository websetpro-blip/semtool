# app/widgets/keys_panel_new.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
                               QTreeView, QLineEdit, QMenu, QLabel, QHBoxLayout, QPushButton)
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QPoint

class KeysPanelNew(QWidget):
    """Правая панель с вкладками Группы/Ключи как в Key Collector"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Вкладки
        self.tabs = QTabWidget()
        self.tabs.setMovable(False)
        
        # === Вкладка "Ключи" ===
        keys_widget = QWidget()
        keys_layout = QVBoxLayout(keys_widget)
        
        # Фильтр
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Фильтр по фразам...")
        
        # Таблица ключей
        self.keys_table = QTableWidget(0, 5)
        self.keys_table.setHorizontalHeaderLabels(["Фраза", "WS", '"WS"', "!WS", "Статус"])
        self.keys_table.verticalHeader().setVisible(False)
        self.keys_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.keys_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.keys_table.setAlternatingRowColors(True)
        
        # Кнопки действий
        keys_buttons = QHBoxLayout()
        btn_copy = QPushButton("📋 Копировать")
        btn_depth = QPushButton("🔍 Вглубь")
        keys_buttons.addWidget(btn_copy)
        keys_buttons.addWidget(btn_depth)
        keys_buttons.addStretch()
        
        keys_layout.addWidget(self.filter)
        keys_layout.addWidget(self.keys_table, 1)
        keys_layout.addLayout(keys_buttons)
        
        # === Вкладка "Группы" ===
        groups_widget = QWidget()
        groups_layout = QVBoxLayout(groups_widget)
        
        # Модель для дерева
        self.groups_model = QStandardItemModel()
        self.groups_model.setHorizontalHeaderLabels(["Группа / Фраза", "Кол-во"])
        
        # Дерево групп
        self.groups_tree = QTreeView()
        self.groups_tree.setModel(self.groups_model)
        self.groups_tree.setHeaderHidden(False)
        self.groups_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.groups_tree.customContextMenuRequested.connect(self._groups_context_menu)
        
        # Кнопки управления группами
        groups_buttons = QHBoxLayout()
        btn_new_group = QPushButton("➕ Новая группа")
        btn_rename = QPushButton("✏️ Переименовать")
        btn_delete = QPushButton("🗑️ Удалить")
        groups_buttons.addWidget(btn_new_group)
        groups_buttons.addWidget(btn_rename)
        groups_buttons.addWidget(btn_delete)
        groups_buttons.addStretch()
        
        groups_layout.addWidget(QLabel("Группы (кластеризатор)"))
        groups_layout.addWidget(self.groups_tree, 1)
        groups_layout.addLayout(groups_buttons)
        
        # Добавляем вкладки
        self.tabs.addTab(groups_widget, "Группы")
        self.tabs.addTab(keys_widget, "Ключи")
        
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabs, 1)
        
        # Данные
        self._all_keys = []
        
        # Подключаем фильтр
        self.filter.textChanged.connect(self._apply_filter)
    
    def load_keys(self, rows):
        """Загрузить ключи в таблицу"""
        self._all_keys = rows
        self._render_keys(rows)
    
    def load_groups(self, groups: dict):
        """Загрузить группы в дерево"""
        self.groups_model.removeRows(0, self.groups_model.rowCount())
        
        for group_id, group_data in sorted(groups.items()):
            # Корневой элемент группы
            root = QStandardItem(group_data["name"])
            root.setEditable(False)
            count = QStandardItem(str(len(group_data["phrases"])))
            count.setEditable(False)
            
            # Добавляем фразы
            for phrase in group_data["phrases"]:
                child = QStandardItem(phrase)
                child.setEditable(False)
                empty = QStandardItem("")
                root.appendRow([child, empty])
            
            self.groups_model.appendRow([root, count])
        
        self.groups_tree.expandAll()
    
    def selected_phrases(self) -> list[str]:
        """Получить выбранные фразы"""
        rows = set()
        for index in self.keys_table.selectedIndexes():
            rows.add(index.row())
        
        phrases = []
        for row in rows:
            item = self.keys_table.item(row, 0)
            if item:
                phrases.append(item.text())
        
        return phrases
    
    def _render_keys(self, rows):
        """Отрисовать таблицу ключей"""
        self.keys_table.setRowCount(len(rows))
        
        for i, row in enumerate(rows):
            values = [
                row["phrase"],
                str(row.get("ws", 0)),
                str(row.get("qws", 0)),
                str(row.get("bws", 0)),
                row.get("status", "")
            ]
            for j, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if j > 0 and j < 4:  # Числовые колонки
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.keys_table.setItem(i, j, item)
        
        self.keys_table.resizeColumnsToContents()
    
    def _apply_filter(self, text):
        """Применить фильтр к таблице"""
        text = (text or "").lower().strip()
        
        if text:
            filtered = [r for r in self._all_keys if text in r["phrase"].lower()]
        else:
            filtered = self._all_keys
        
        self._render_keys(filtered)
    
    def _groups_context_menu(self, pos: QPoint):
        """Контекстное меню для групп"""
        menu = QMenu(self)
        
        action_depth = QAction("🔍 Парсинг вглубь", self)
        action_group = QAction("📁 В группу...", self)
        action_minus = QAction("➖ Минусовать...", self)
        action_export = QAction("💾 Экспорт группы", self)
        
        menu.addAction(action_depth)
        menu.addAction(action_group)
        menu.addAction(action_minus)
        menu.addSeparator()
        menu.addAction(action_export)
        
        menu.exec(self.groups_tree.mapToGlobal(pos))

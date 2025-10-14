"""
Правая панель с ключевыми фразами (как в Key Collector)
Отображает результаты парсинга во всю высоту справа от вкладок
Вкладки: Ключи и Группы (файл 45)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QLabel, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog, QComboBox
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QAction, QColor


class KeysPanel(QWidget):
    """Правая панель с ключами во всю высоту (как в Key Collector - файл 45)"""
    
    # Сигналы
    phrase_selected = Signal(str)  # Фраза выбрана
    phrases_filtered = Signal(int)  # Количество отфильтрованных фраз
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(400)
        self.setMaximumWidth(600)
        
        # Данные
        self._groups = {}  # Группы: {group_name: [phrases]}
        
        self.setup_ui()
    
    def setup_ui(self):
        """Создание интерфейса - ТОЛЬКО ГРУППЫ справа (как в Key Collector)"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Заголовок "Управление группами" (как в Key Collector)
        header_layout = QHBoxLayout()
        title = QLabel("Управление группами")
        title.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Фильтр "Все" (как в Key Collector)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Все", "С фразами", "Пустые", "Корзина"])
        layout.addWidget(self.filter_combo)
        
        # Поиск по группам
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по группам...")
        self.search_edit.textChanged.connect(self._filter_groups)
        layout.addWidget(self.search_edit)
        
        # Дерево групп (без колонок, как в Key Collector)
        self.groups_tree = QTreeWidget()
        self.groups_tree.setHeaderHidden(True)  # Скрываем заголовки
        self.groups_tree.setColumnCount(1)      # Одна колонка
        self.groups_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.groups_tree.customContextMenuRequested.connect(self._groups_context_menu)
        self.groups_tree.setAlternatingRowColors(True)
        self.groups_tree.setAnimated(True)
        
        layout.addWidget(self.groups_tree, 1)
        
        # Кнопки управления группами
        groups_actions = QHBoxLayout()
        
        create_group_btn = QPushButton("➕ Создать")
        create_group_btn.setToolTip("Создать новую группу")
        create_group_btn.clicked.connect(self._create_group_in_tree)
        groups_actions.addWidget(create_group_btn)
        
        rename_group_btn = QPushButton("✏️ Переименовать")
        rename_group_btn.setToolTip("Переименовать группу")
        rename_group_btn.clicked.connect(self._rename_group)
        groups_actions.addWidget(rename_group_btn)
        
        delete_group_btn = QPushButton("🗑️ Удалить")
        delete_group_btn.setToolTip("Удалить группу")
        delete_group_btn.clicked.connect(self._delete_group_from_tree)
        groups_actions.addWidget(delete_group_btn)
        
        groups_actions.addStretch()
        
        layout.addLayout(groups_actions)
    
    def _filter_groups(self, text: str):
        """Фильтровать группы по поисковому запросу"""
        text = text.lower().strip()
        
        # Если поиск пустой, показываем все
        if not text:
            for i in range(self.groups_tree.topLevelItemCount()):
                self.groups_tree.topLevelItem(i).setHidden(False)
            return
        
        # Фильтруем группы
        for i in range(self.groups_tree.topLevelItemCount()):
            item = self.groups_tree.topLevelItem(i)
            group_name = item.text(0).lower()
            
            # Проверяем название группы
            if text in group_name:
                item.setHidden(False)
                continue
            
            # Проверяем фразы внутри группы
            has_match = False
            for j in range(item.childCount()):
                child = item.child(j)
                phrase = child.text(0).lower()
                if text in phrase:
                    has_match = True
                    break
            
            item.setHidden(not has_match)
    
    def clear(self):
        """Очистить панель"""
        self.groups_tree.clear()
        self._groups = {}
        self._render_groups()  # Перерисовать (с Корзиной)
    
    # === МЕТОДЫ ДЛЯ ВКЛАДКИ "ГРУППЫ" (файл 45) ===
    
    def load_groups(self, groups: dict):
        """
        Загрузить группы в дерево
        
        Args:
            groups: {group_name: [phrases]} или {cluster_id: {'name': str, 'phrases': [...]}}
        """
        self._groups = groups
        self._render_groups()
    
    def _render_groups(self):
        """Отрисовать дерево групп (как в Key Collector)"""
        self.groups_tree.clear()
        
        # Добавляем "Корзина (0)" первой (как в Key Collector)
        trash_item = QTreeWidgetItem([f"Корзина (0 / 0)"])
        trash_item.setForeground(0, QColor("#999"))  # Серый цвет
        self.groups_tree.addTopLevelItem(trash_item)
        
        for group_name, data in self._groups.items():
            # Поддержка двух форматов
            if isinstance(data, dict):
                name = data.get('name', str(group_name))
                phrases = data.get('phrases', [])
            else:
                name = str(group_name)
                phrases = data if isinstance(data, list) else []
            
            phrase_count = len(phrases)
            
            # Суммируем частотность WS всех фраз в группе
            freq_sum = 0
            for phrase_item in phrases:
                if isinstance(phrase_item, dict):
                    freq_sum += phrase_item.get('freq_total', 0)
                # Если это просто строка (старый формат), частотность = 0
            
            # Корневой элемент: "название (фраз / частотность)" - КАК В KEY COLLECTOR
            root_item = QTreeWidgetItem([f"{name} ({phrase_count} / {freq_sum})"])
            root_item.setExpanded(False)
            
            # Добавляем фразы как дочерние элементы
            for phrase_item in phrases[:10]:  # Первые 10 для скорости
                # Поддержка старого (строка) и нового (dict) формата
                if isinstance(phrase_item, dict):
                    phrase_text = phrase_item.get('phrase', str(phrase_item))
                    freq = phrase_item.get('freq_total', 0)
                    # Показываем частотность если есть
                    if freq > 0:
                        child_item = QTreeWidgetItem([f"  {phrase_text} ({freq})"])
                    else:
                        child_item = QTreeWidgetItem([f"  {phrase_text}"])
                else:
                    # Старый формат - просто строка
                    child_item = QTreeWidgetItem([f"  {phrase_item}"])
                root_item.addChild(child_item)
            
            # Если фраз больше 10, добавляем "..."
            if len(phrases) > 10:
                more_item = QTreeWidgetItem([f"  ... еще {len(phrases) - 10} фраз"])
                root_item.addChild(more_item)
            
            self.groups_tree.addTopLevelItem(root_item)
    
    def _groups_context_menu(self, pos: QPoint):
        """Контекстное меню на дереве групп"""
        menu = QMenu(self)
        
        item = self.groups_tree.itemAt(pos)
        
        # Создать группу
        create_action = QAction("➕ Создать группу", self)
        create_action.triggered.connect(self._create_group_in_tree)
        menu.addAction(create_action)
        
        if item:
            # Если это корневой элемент (группа)
            if item.parent() is None:
                # Переименовать
                rename_action = QAction("✏️ Переименовать", self)
                rename_action.triggered.connect(self._rename_group)
                menu.addAction(rename_action)
                
                # Удалить
                delete_action = QAction("🗑️ Удалить группу", self)
                delete_action.triggered.connect(self._delete_group_from_tree)
                menu.addAction(delete_action)
                
                menu.addSeparator()
                
                # Экспорт группы
                export_action = QAction("📥 Экспортировать группу", self)
                export_action.triggered.connect(lambda: self._export_group(item))
                menu.addAction(export_action)
        
        menu.exec(self.groups_tree.mapToGlobal(pos))
    
    def _create_group_in_tree(self):
        """Создать новую группу"""
        name, ok = QInputDialog.getText(
            self,
            "Новая группа",
            "Название группы:"
        )
        
        if ok and name.strip():
            name = name.strip()
            if name in self._groups:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Ошибка", f"Группа '{name}' уже существует")
                return
            
            # Создаем пустую группу
            self._groups[name] = []
            self._render_groups()
            
            print(f"[OK] Создана группа: {name}")
    
    def _rename_group(self):
        """Переименовать выбранную группу"""
        item = self.groups_tree.currentItem()
        if not item or item.parent() is not None:
            return
        
        old_name = item.text(0)
        new_name, ok = QInputDialog.getText(
            self,
            "Переименовать группу",
            "Новое название:",
            text=old_name
        )
        
        if ok and new_name.strip() and new_name != old_name:
            new_name = new_name.strip()
            
            if new_name in self._groups:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Ошибка", f"Группа '{new_name}' уже существует")
                return
            
            # Переименовываем
            self._groups[new_name] = self._groups.pop(old_name)
            self._render_groups()
            
            print(f"[OK] Группа переименована: {old_name} → {new_name}")
    
    def _delete_group_from_tree(self):
        """Удалить выбранную группу"""
        item = self.groups_tree.currentItem()
        if not item or item.parent() is not None:
            return
        
        group_name = item.text(0)
        
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Удалить группу",
            f"Удалить группу '{group_name}' ({item.text(1)} фраз)?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if group_name in self._groups:
                del self._groups[group_name]
                self._render_groups()
                print(f"[OK] Группа удалена: {group_name}")
    
    def _export_group(self, item: QTreeWidgetItem):
        """Экспортировать группу в CSV"""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from pathlib import Path
        import csv
        
        group_name = item.text(0)
        phrases = self._groups.get(group_name, [])
        
        if isinstance(phrases, dict):
            phrases = phrases.get('phrases', [])
        
        if not phrases:
            QMessageBox.warning(self, "Экспорт", "Группа пуста")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт группы",
            str(Path.home() / f"{group_name}.csv"),
            "CSV files (*.csv)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Фраза'])
                    for phrase in phrases:
                        writer.writerow([str(phrase)])
                
                QMessageBox.information(
                    self,
                    "Экспорт",
                    f"Экспортировано {len(phrases)} фраз из группы '{group_name}'"
                )
            except Exception as e:
                QMessageBox.warning(self, "Ошибка экспорта", str(e))

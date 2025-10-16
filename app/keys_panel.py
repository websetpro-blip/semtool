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
from PySide6.QtGui import QAction, QColor, QFont, QIcon


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
        
        # ДЕРЕВО групп с раскрытием (как в Key Collector!)
        self.groups_tree = QTreeWidget()
        self.groups_tree.setHeaderLabels(["Группа / Фраза", ""])  # 2 колонки
        self.groups_tree.setColumnWidth(0, 300)
        self.groups_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.groups_tree.customContextMenuRequested.connect(self._groups_context_menu)
        self.groups_tree.setAlternatingRowColors(True)
        self.groups_tree.setRootIsDecorated(True)  # Показываем стрелки раскрытия
        self.groups_tree.setIndentation(15)
        
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
        
        # Фильтруем дерево
        root = self.groups_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            group_name = item.text(0).lower()
            
            # Показываем/скрываем в зависимости от поиска
            if not text or text in group_name:
                item.setHidden(False)
            else:
                item.setHidden(True)
    
    def clear(self):
        """Очистить панель"""
        self.groups_list.clear()
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
        """Отрисовать ДЕРЕВО групп с фразами (как в Key Collector!)"""
        self.groups_tree.clear()
        
        # Добавляем "Корзина (0)" первой (как в Key Collector)
        trash = QTreeWidgetItem(["Корзина (0)", ""])
        trash.setForeground(0, QColor("#999"))
        self.groups_tree.addTopLevelItem(trash)
        
        for group_name, data in self._groups.items():
            # Поддержка двух форматов
            if isinstance(data, dict):
                name = data.get('name', str(group_name))
                phrases = data.get('phrases', [])
            else:
                name = str(group_name)
                phrases = data if isinstance(data, list) else []
            
            # Формат: "название (количество)"
            count = len(phrases)
            
            # Создаем корневой элемент группы
            group_item = QTreeWidgetItem([f"{name} ({count})", ""])
            
            # Применяем стиль к группе
            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)
            
            # Цвет по умолчанию для группы
            group_color = data.get('color') if isinstance(data, dict) else None
            if group_color:
                group_item.setBackground(0, QColor(group_color))
            
            if count == 0:
                group_item.setForeground(0, QColor("#999"))
            
            # Добавляем фразы как дочерние элементы
            for phrase_data in phrases:
                phrase_text = phrase_data.get("phrase", phrase_data) if isinstance(phrase_data, dict) else phrase_data
                
                # Создаем элемент фразы
                phrase_item = QTreeWidgetItem([phrase_text, ""])
                phrase_item.setForeground(0, QColor("#ddd"))
                
                group_item.addChild(phrase_item)
            
            self.groups_tree.addTopLevelItem(group_item)
        
        # Раскрываем все группы по умолчанию
        self.groups_tree.expandAll()
    
    def _groups_context_menu(self, pos: QPoint):
        """Контекстное меню на дереве групп"""
        menu = QMenu(self)
        
        item = self.groups_tree.itemAt(pos)
        
        # Создать группу
        create_action = QAction("➕ Создать группу", self)
        create_action.triggered.connect(self._create_group_in_tree)
        menu.addAction(create_action)
        
        if item and not item.parent():  # Только для групп, не для фраз
            menu.addSeparator()
            
            # Переименовать
            rename_action = QAction("✏️ Переименовать", self)
            rename_action.triggered.connect(self._rename_group)
            menu.addAction(rename_action)
            
            # Назначить цвет (как в Key Collector!)
            color_menu = QMenu("🎨 Назначить цвет", self)
            
            # Предустановленные цвета
            colors = [
                ("#FFD700", "Желтый"),
                ("#90EE90", "Зеленый"),
                ("#87CEEB", "Голубой"),
                ("#FFA500", "Оранжевый"),
                ("#FF69B4", "Розовый"),
                ("#DDA0DD", "Сиреневый"),
                ("#F0E68C", "Бежевый"),
                ("", "Без цвета")
            ]
            
            for color_code, color_name in colors:
                color_action = QAction(color_name, self)
                if color_code:
                    # Показываем цвет в иконке
                    from PySide6.QtGui import QPixmap, QPainter
                    pixmap = QPixmap(16, 16)
                    pixmap.fill(QColor(color_code))
                    color_action.setIcon(QIcon(pixmap))
                color_action.triggered.connect(lambda checked, c=color_code: self._set_group_color(c))
                color_menu.addAction(color_action)
            
            menu.addMenu(color_menu)
            
            menu.addSeparator()
            
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
        if not item or item.parent():  # Игнорируем если это фраза, а не группа
            return
        
        old_name = item.text(0).split(" (")[0]  # Убираем счетчик
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
        if not item or item.parent():  # Игнорируем если это фраза
            return
        
        group_name = item.text(0).split(" (")[0]
        phrases_count = item.childCount()
        
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Удалить группу",
            f"Удалить группу '{group_name}' ({phrases_count} фраз)?",
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

    def _set_group_color(self, color_code: str):
        """Назначить цвет группе (как в Key Collector)"""
        item = self.groups_tree.currentItem()
        if not item or item.parent():  # Только для групп
            return
        
        group_name = item.text(0).split(" (")[0]
        
        # Применяем цвет
        if color_code:
            item.setBackground(0, QColor(color_code))
            # Сохраняем в данных группы
            if group_name in self._groups:
                if isinstance(self._groups[group_name], dict):
                    self._groups[group_name]['color'] = color_code
                else:
                    # Конвертируем в dict формат
                    self._groups[group_name] = {
                        'name': group_name,
                        'phrases': self._groups[group_name],
                        'color': color_code
                    }
        else:
            # Убираем цвет
            item.setBackground(0, QColor("transparent"))
            if group_name in self._groups and isinstance(self._groups[group_name], dict):
                self._groups[group_name].pop('color', None)
        
        print(f"[OK] Цвет группы '{group_name}' изменен на {color_code or 'без цвета'}")


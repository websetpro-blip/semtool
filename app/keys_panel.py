"""
Правая панель с ключевыми фразами (как в Key Collector)
Отображает результаты парсинга во всю высоту справа от вкладок
Вкладки: Ключи и Группы (файл 45)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QLabel, QHeaderView, QHBoxLayout, QPushButton,
    QComboBox, QAbstractItemView, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QMenu, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QColor, QAction, QStandardItemModel, QStandardItem


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
        self._all_data = []  # Все фразы
        self._filtered_data = []  # Отфильтрованные фразы
        self._groups = {}  # Группы: {group_name: [phrases]}
        
        self.setup_ui()
    
    def setup_ui(self):
        """Создание интерфейса (как в Key Collector - файл 45)"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # ВКЛАДКИ: Ключи и Группы (файл 45)
        self.tabs = QTabWidget()
        self.tabs.setMovable(False)
        
        # === ВКЛАДКА "КЛЮЧИ" ===
        keys_widget = QWidget()
        keys_layout = QVBoxLayout(keys_widget)
        keys_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок на вкладке Ключи
        header_layout = QHBoxLayout()
        title = QLabel("Ключевые фразы")
        title.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(title)
        
        self.count_label = QLabel("0 фраз")
        self.count_label.setStyleSheet("color: gray;")
        header_layout.addStretch()
        header_layout.addWidget(self.count_label)
        
        keys_layout.addLayout(header_layout)
        
        # Панель фильтров
        filter_layout = QHBoxLayout()
        
        # Поиск
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по фразам...")
        self.search_edit.textChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.search_edit, 3)
        
        # Фильтр по статусу
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Все", "Готово", "В очереди", "Ошибка"])
        self.status_combo.currentTextChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.status_combo, 1)
        
        # Кнопка очистки
        clear_btn = QPushButton("✖")
        clear_btn.setMaximumWidth(30)
        clear_btn.setToolTip("Очистить фильтры")
        clear_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(clear_btn)
        
        keys_layout.addLayout(filter_layout)
        
        # Таблица с фразами
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Фраза", "WS", '"WS"', "!WS", "Статус", "Группа"
        ])
        
        # Убираем белый фон ячеек - делаем прозрачным (как в основном софте)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                gridline-color: #3a3a3a;
            }
            QTableWidget::item {
                background-color: transparent;
                border: none;
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #0d47a1;
            }
        """)
        
        # Настройка колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Фраза растягивается
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # WS
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # "WS"
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # !WS
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Статус
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Группа
        
        # Настройка таблицы
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # Сортировка по клику на заголовок
        self.table.setSortingEnabled(True)
        
        # Двойной клик на фразе
        self.table.cellDoubleClicked.connect(self._on_phrase_double_click)
        
        keys_layout.addWidget(self.table, 1)
        
        # Панель действий
        actions_layout = QHBoxLayout()
        
        # Группировка
        group_btn = QPushButton("📁 Создать группу")
        group_btn.setToolTip("Назначить группу выбранным фразам")
        group_btn.clicked.connect(self._create_group)
        actions_layout.addWidget(group_btn)
        
        export_btn = QPushButton("📥 Экспорт")
        export_btn.setToolTip("Экспортировать в CSV")
        export_btn.clicked.connect(self._export_to_csv)
        actions_layout.addWidget(export_btn)
        
        copy_btn = QPushButton("📋 Копировать")
        copy_btn.setToolTip("Копировать выбранные фразы")
        copy_btn.clicked.connect(self._copy_selected)
        actions_layout.addWidget(copy_btn)
        
        actions_layout.addStretch()
        
        keys_layout.addLayout(actions_layout)
        
        # === ВКЛАДКА "ГРУППЫ" (файл 45) ===
        groups_widget = QWidget()
        groups_layout = QVBoxLayout(groups_widget)
        groups_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок
        groups_header = QHBoxLayout()
        groups_title = QLabel("Группы")
        groups_title.setStyleSheet("font-weight: bold;")
        groups_header.addWidget(groups_title)
        
        self.groups_count_label = QLabel("0 групп")
        self.groups_count_label.setStyleSheet("color: gray;")
        groups_header.addStretch()
        groups_header.addWidget(self.groups_count_label)
        
        groups_layout.addLayout(groups_header)
        
        # Дерево групп (иерархия)
        self.groups_tree = QTreeWidget()
        self.groups_tree.setHeaderLabels(["Группа / Фраза", "Фраз"])
        self.groups_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.groups_tree.customContextMenuRequested.connect(self._groups_context_menu)
        self.groups_tree.setAlternatingRowColors(True)
        self.groups_tree.setAnimated(True)
        
        groups_layout.addWidget(self.groups_tree, 1)
        
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
        
        groups_layout.addLayout(groups_actions)
        
        # === ДОБАВЛЯЕМ ВКЛАДКИ ===
        self.tabs.addTab(keys_widget, "Ключи")
        self.tabs.addTab(groups_widget, "Группы")
        
        layout.addWidget(self.tabs)
    
    def load_data(self, data: list[dict]):
        """
        Загрузить данные из БД
        
        Args:
            data: Список словарей с ключами:
                - phrase: str
                - freq_total: int (WS)
                - freq_quotes: int ("WS")
                - freq_exact: int (!WS)
                - status: str
                - group: str (опционально)
        """
        self._all_data = data
        self._apply_filter()
    
    def _apply_filter(self):
        """Применить фильтры"""
        search_text = self.search_edit.text().lower().strip()
        status_filter = self.status_combo.currentText()
        
        # Фильтрация
        filtered = []
        for row in self._all_data:
            phrase = row.get('phrase', '').lower()
            status = row.get('status', '')
            
            # Фильтр по поиску
            if search_text and search_text not in phrase:
                continue
            
            # Фильтр по статусу
            if status_filter != "Все":
                status_map = {
                    "Готово": "ok",
                    "В очереди": "queued",
                    "Ошибка": "error"
                }
                if status != status_map.get(status_filter, status_filter):
                    continue
            
            filtered.append(row)
        
        self._filtered_data = filtered
        self._render_table()
    
    def _render_table(self):
        """Отрисовать таблицу"""
        self.table.setSortingEnabled(False)  # Отключаем сортировку при заполнении
        self.table.setRowCount(len(self._filtered_data))
        
        for i, row in enumerate(self._filtered_data):
            # Фраза
            phrase_item = QTableWidgetItem(row.get('phrase', ''))
            self.table.setItem(i, 0, phrase_item)
            
            # WS
            ws = row.get('freq_total', 0)
            ws_item = QTableWidgetItem(f"{ws:,}" if ws > 0 else "")
            ws_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 1, ws_item)
            
            # "WS"
            qws = row.get('freq_quotes', 0)
            qws_item = QTableWidgetItem(f"{qws:,}" if qws > 0 else "")
            qws_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 2, qws_item)
            
            # !WS
            bws = row.get('freq_exact', 0)
            bws_item = QTableWidgetItem(f"{bws:,}" if bws > 0 else "")
            bws_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(i, 3, bws_item)
            
            # Статус
            status = row.get('status', '')
            status_map = {
                'ok': 'Готово',
                'queued': 'В очереди',
                'running': 'Парсинг...',
                'error': 'Ошибка'
            }
            status_text = status_map.get(status, status)
            status_item = QTableWidgetItem(status_text)
            
            # Цвет статуса
            if status == 'ok':
                status_item.setForeground(QColor("#4CAF50"))
            elif status == 'error':
                status_item.setForeground(QColor("#F44336"))
            elif status == 'running':
                status_item.setForeground(QColor("#FF9800"))
            
            self.table.setItem(i, 4, status_item)
            
            # Группа
            group = row.get('group', '')
            group_item = QTableWidgetItem(str(group) if group else "")
            self.table.setItem(i, 5, group_item)
        
        self.table.setSortingEnabled(True)  # Включаем сортировку обратно
        
        # Обновляем счетчик
        total = len(self._all_data)
        filtered = len(self._filtered_data)
        if filtered < total:
            self.count_label.setText(f"{filtered} из {total} фраз")
        else:
            self.count_label.setText(f"{total} фраз")
        
        self.phrases_filtered.emit(filtered)
    
    def _clear_filters(self):
        """Очистить фильтры"""
        self.search_edit.clear()
        self.status_combo.setCurrentIndex(0)
    
    def _on_phrase_double_click(self, row, col):
        """Двойной клик на фразе"""
        if 0 <= row < len(self._filtered_data):
            phrase = self._filtered_data[row].get('phrase', '')
            self.phrase_selected.emit(phrase)
    
    def _copy_selected(self):
        """Копировать выбранные фразы в буфер обмена"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        phrases = []
        for row in sorted(selected_rows):
            if 0 <= row < len(self._filtered_data):
                phrases.append(self._filtered_data[row].get('phrase', ''))
        
        if phrases:
            from PySide6.QtGui import QClipboard
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText('\n'.join(phrases))
            print(f"[OK] Скопировано {len(phrases)} фраз в буфер обмена")
    
    def _export_to_csv(self):
        """Экспортировать в CSV"""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from pathlib import Path
        import csv
        
        if not self._filtered_data:
            QMessageBox.warning(self, "Экспорт", "Нет данных для экспорта")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт в CSV",
            str(Path.home() / "keywords.csv"),
            "CSV files (*.csv)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Фраза', 'WS', '"WS"', '!WS', 'Статус', 'Группа'])
                    
                    for row in self._filtered_data:
                        writer.writerow([
                            row.get('phrase', ''),
                            row.get('freq_total', 0),
                            row.get('freq_quotes', 0),
                            row.get('freq_exact', 0),
                            row.get('status', ''),
                            row.get('group', '')
                        ])
                
                QMessageBox.information(self, "Экспорт", f"Экспортировано {len(self._filtered_data)} фраз в {filename}")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка экспорта", str(e))
    
    def _create_group(self):
        """Создать/назначить группу выбранным фразам"""
        from PySide6.QtWidgets import QInputDialog, QMessageBox
        
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "Группировка", "Выберите фразы для группировки")
            return
        
        # Получаем список существующих групп
        from ..services import frequency as frequency_service
        existing_groups = frequency_service.get_all_groups()
        
        # Диалог для ввода/выбора группы
        group_name, ok = QInputDialog.getItem(
            self,
            "Создать группу",
            "Название группы:",
            existing_groups + ["<Новая группа>"],
            0,
            True  # Editable
        )
        
        if ok and group_name:
            # Если выбрали "<Новая группа>", просим ввести имя
            if group_name == "<Новая группа>":
                group_name, ok = QInputDialog.getText(
                    self,
                    "Новая группа",
                    "Введите название новой группы:"
                )
                if not ok or not group_name:
                    return
            
            # Получаем ID выбранных фраз
            phrase_ids = []
            for row in selected_rows:
                if 0 <= row < len(self._filtered_data):
                    # TODO: Нужен способ получить ID фразы
                    # Пока используем mask как идентификатор
                    pass
            
            # Обновляем группу в БД
            # TODO: Нужно передавать ID фраз, а не mask
            # Пока просто обновим локальные данные
            for row in selected_rows:
                if 0 <= row < len(self._filtered_data):
                    self._filtered_data[row]['group'] = group_name
            
            # Перерисовываем таблицу
            self._render_table()
            
            QMessageBox.information(
                self,
                "Группировка",
                f"Назначена группа '{group_name}' для {len(selected_rows)} фраз"
            )
    
    def clear(self):
        """Очистить панель"""
        self._all_data = []
        self._filtered_data = []
        self.table.setRowCount(0)
        self.count_label.setText("0 фраз")
        self.groups_tree.clear()
        self._groups = {}
        self.groups_count_label.setText("0 групп")
    
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
        """Отрисовать дерево групп"""
        self.groups_tree.clear()
        
        if not self._groups:
            self.groups_count_label.setText("0 групп")
            return
        
        for group_name, data in self._groups.items():
            # Поддержка двух форматов
            if isinstance(data, dict):
                name = data.get('name', str(group_name))
                phrases = data.get('phrases', [])
            else:
                name = str(group_name)
                phrases = data if isinstance(data, list) else []
            
            # Создаем корневой элемент группы
            root_item = QTreeWidgetItem([name, str(len(phrases))])
            root_item.setExpanded(False)
            
            # Добавляем фразы как дочерние элементы
            for phrase in phrases:
                child_item = QTreeWidgetItem([str(phrase), ""])
                root_item.addChild(child_item)
            
            self.groups_tree.addTopLevelItem(root_item)
        
        # Обновляем счетчик
        count = len(self._groups)
        self.groups_count_label.setText(f"{count} групп" if count != 1 else "1 группа")
    
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

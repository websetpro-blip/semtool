# app/widgets/geo_tree.py
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QLineEdit
from PySide6.QtCore import Qt
import json
from pathlib import Path

class GeoTree(QWidget):
    """Дерево регионов с чекбоксами как в Key Collector"""
    
    def __init__(self, regions_path: str = "data/regions_tree.json", parent=None):
        super().__init__(parent)
        self._regions_path = Path(regions_path)
        
        # Поиск
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по регионам...")
        
        # Дерево
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.search)
        layout.addWidget(self.tree, 1)
        
        self._load()
        self.search.textChanged.connect(self._filter)

    def _load(self):
        """Загрузить регионы из JSON"""
        if not self._regions_path.exists():
            # Создаем дефолтный файл с основными регионами
            default_regions = [
                {"id": 225, "name": "Россия", "children": [
                    {"id": 213, "name": "Москва"},
                    {"id": 2, "name": "Санкт-Петербург"},
                    {"id": 54, "name": "Екатеринбург"},
                    {"id": 56, "name": "Челябинск"},
                    {"id": 65, "name": "Новосибирск"},
                    {"id": 66, "name": "Нижний Новгород"},
                    {"id": 172, "name": "Уфа"},
                    {"id": 35, "name": "Краснодар"},
                    {"id": 39, "name": "Ростов-на-Дону"},
                    {"id": 47, "name": "Казань"}
                ]},
                {"id": 187, "name": "Украина", "children": [
                    {"id": 143, "name": "Киев"},
                    {"id": 144, "name": "Харьков"},
                    {"id": 145, "name": "Днепр"}
                ]},
                {"id": 149, "name": "Беларусь", "children": [
                    {"id": 157, "name": "Минск"}
                ]},
                {"id": 159, "name": "Казахстан", "children": [
                    {"id": 162, "name": "Алматы"},
                    {"id": 163, "name": "Нур-Султан"}
                ]}
            ]
            self._regions_path.parent.mkdir(parents=True, exist_ok=True)
            self._regions_path.write_text(json.dumps(default_regions, ensure_ascii=False, indent=2), encoding="utf-8")
        
        data = json.loads(self._regions_path.read_text(encoding="utf-8"))
        self.tree.clear()
        
        for top in data:
            root = QTreeWidgetItem([f"{top['name']} ({top['id']})"])
            root.setCheckState(0, Qt.Unchecked)
            root.setData(0, Qt.UserRole, top['id'])
            
            for child in top.get("children", []):
                item = QTreeWidgetItem([f"{child['name']} ({child['id']})"])
                item.setCheckState(0, Qt.Unchecked)
                item.setData(0, Qt.UserRole, child['id'])
                root.addChild(item)
            
            self.tree.addTopLevelItem(root)
        
        self.tree.expandAll()

    def _filter(self, text: str):
        """Фильтровать дерево по поисковому запросу"""
        text = (text or "").lower().strip()
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            self._apply_filter_node(root.child(i), text)

    def _apply_filter_node(self, node, term):
        """Применить фильтр к узлу и его детям"""
        visible = term in node.text(0).lower()
        for i in range(node.childCount()):
            if self._apply_filter_node(node.child(i), term):
                visible = True
        node.setHidden(not visible)
        return visible

    def selected_geo_ids(self) -> list[int]:
        """Получить выбранные ID регионов"""
        ids = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            ids.extend(self._collect_ids(root.child(i)))
        return ids or [225]  # По умолчанию Россия
    
    def _collect_ids(self, node):
        """Собрать ID отмеченных узлов"""
        ids = []
        if node.checkState(0) == Qt.Checked:
            node_id = node.data(0, Qt.UserRole)
            if node_id:
                ids.append(node_id)
        for i in range(node.childCount()):
            ids.extend(self._collect_ids(node.child(i)))
        return ids

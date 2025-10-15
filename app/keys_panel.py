"""
Р СџРЎР‚Р В°Р Р†Р В°РЎРЏ Р С—Р В°Р Р…Р ВµР В»РЎРЉ РЎРѓ Р С”Р В»РЎР‹РЎвЂЎР ВµР Р†РЎвЂ№Р СР С‘ РЎвЂћРЎР‚Р В°Р В·Р В°Р СР С‘ (Р С”Р В°Р С” Р Р† Key Collector)
Р С›РЎвЂљР С•Р В±РЎР‚Р В°Р В¶Р В°Р ВµРЎвЂљ РЎР‚Р ВµР В·РЎС“Р В»РЎРЉРЎвЂљР В°РЎвЂљРЎвЂ№ Р С—Р В°РЎР‚РЎРѓР С‘Р Р…Р С–Р В° Р Р†Р С• Р Р†РЎРѓРЎР‹ Р Р†РЎвЂ№РЎРѓР С•РЎвЂљРЎС“ РЎРѓР С—РЎР‚Р В°Р Р†Р В° Р С•РЎвЂљ Р Р†Р С”Р В»Р В°Р Т‘Р С•Р С”
Р вЂ™Р С”Р В»Р В°Р Т‘Р С”Р С‘: Р С™Р В»РЎР‹РЎвЂЎР С‘ Р С‘ Р вЂњРЎР‚РЎС“Р С—Р С—РЎвЂ№ (РЎвЂћР В°Р в„–Р В» 45)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QLabel, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog, QComboBox
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QAction, QColor, QFont, QIcon


class KeysPanel(QWidget):
    """Р СџРЎР‚Р В°Р Р†Р В°РЎРЏ Р С—Р В°Р Р…Р ВµР В»РЎРЉ РЎРѓ Р С”Р В»РЎР‹РЎвЂЎР В°Р СР С‘ Р Р†Р С• Р Р†РЎРѓРЎР‹ Р Р†РЎвЂ№РЎРѓР С•РЎвЂљРЎС“ (Р С”Р В°Р С” Р Р† Key Collector - РЎвЂћР В°Р в„–Р В» 45)"""
    
    # Р РЋР С‘Р С–Р Р…Р В°Р В»РЎвЂ№
    phrase_selected = Signal(str)  # Р В¤РЎР‚Р В°Р В·Р В° Р Р†РЎвЂ№Р В±РЎР‚Р В°Р Р…Р В°
    phrases_filtered = Signal(int)  # Р С™Р С•Р В»Р С‘РЎвЂЎР ВµРЎРѓРЎвЂљР Р†Р С• Р С•РЎвЂљРЎвЂћР С‘Р В»РЎРЉРЎвЂљРЎР‚Р С•Р Р†Р В°Р Р…Р Р…РЎвЂ№РЎвЂ¦ РЎвЂћРЎР‚Р В°Р В·
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(400)
        self.setMaximumWidth(600)
        
        # Р вЂќР В°Р Р…Р Р…РЎвЂ№Р Вµ
        self._groups = {}  # Р вЂњРЎР‚РЎС“Р С—Р С—РЎвЂ№: {group_name: [phrases]}
        
        self.setup_ui()
    
    def setup_ui(self):
        """Р РЋР С•Р В·Р Т‘Р В°Р Р…Р С‘Р Вµ Р С‘Р Р…РЎвЂљР ВµРЎР‚РЎвЂћР ВµР в„–РЎРѓР В° - Р СћР С›Р вЂєР В¬Р С™Р С› Р вЂњР В Р Р€Р СџР СџР В« РЎРѓР С—РЎР‚Р В°Р Р†Р В° (Р С”Р В°Р С” Р Р† Key Collector)"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Р вЂ”Р В°Р С–Р С•Р В»Р С•Р Р†Р С•Р С” "Р Р€Р С—РЎР‚Р В°Р Р†Р В»Р ВµР Р…Р С‘Р Вµ Р С–РЎР‚РЎС“Р С—Р С—Р В°Р СР С‘" (Р С”Р В°Р С” Р Р† Key Collector)
        header_layout = QHBoxLayout()
        title = QLabel("Р Р€Р С—РЎР‚Р В°Р Р†Р В»Р ВµР Р…Р С‘Р Вµ Р С–РЎР‚РЎС“Р С—Р С—Р В°Р СР С‘")
        title.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Р В¤Р С‘Р В»РЎРЉРЎвЂљРЎР‚ "Р вЂ™РЎРѓР Вµ" (Р С”Р В°Р С” Р Р† Key Collector)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Р вЂ™РЎРѓР Вµ", "Р РЋ РЎвЂћРЎР‚Р В°Р В·Р В°Р СР С‘", "Р СџРЎС“РЎРѓРЎвЂљРЎвЂ№Р Вµ", "Р С™Р С•РЎР‚Р В·Р С‘Р Р…Р В°"])
        layout.addWidget(self.filter_combo)
        
        # Р СџР С•Р С‘РЎРѓР С” Р С—Р С• Р С–РЎР‚РЎС“Р С—Р С—Р В°Р С
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Р СџР С•Р С‘РЎРѓР С” Р С—Р С• Р С–РЎР‚РЎС“Р С—Р С—Р В°Р С...")
        self.search_edit.textChanged.connect(self._filter_groups)
        layout.addWidget(self.search_edit)
        
        # Р вЂќР вЂўР В Р вЂўР вЂ™Р С› Р С–РЎР‚РЎС“Р С—Р С— РЎРѓ РЎР‚Р В°РЎРѓР С”РЎР‚РЎвЂ№РЎвЂљР С‘Р ВµР С (Р С”Р В°Р С” Р Р† Key Collector!)
        self.groups_tree = QTreeWidget()
        self.groups_tree.setHeaderLabels(["Р вЂњРЎР‚РЎС“Р С—Р С—Р В° / Р В¤РЎР‚Р В°Р В·Р В°", ""])  # 2 Р С”Р С•Р В»Р С•Р Р…Р С”Р С‘
        self.groups_tree.setColumnWidth(0, 300)
        self.groups_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.groups_tree.customContextMenuRequested.connect(self._groups_context_menu)
        self.groups_tree.setAlternatingRowColors(True)
        self.groups_tree.setRootIsDecorated(True)  # Р СџР С•Р С”Р В°Р В·РЎвЂ№Р Р†Р В°Р ВµР С РЎРѓРЎвЂљРЎР‚Р ВµР В»Р С”Р С‘ РЎР‚Р В°РЎРѓР С”РЎР‚РЎвЂ№РЎвЂљР С‘РЎРЏ
        self.groups_tree.setIndentation(15)
        
        layout.addWidget(self.groups_tree, 1)
        
        # Р С™Р Р…Р С•Р С—Р С”Р С‘ РЎС“Р С—РЎР‚Р В°Р Р†Р В»Р ВµР Р…Р С‘РЎРЏ Р С–РЎР‚РЎС“Р С—Р С—Р В°Р СР С‘
        groups_actions = QHBoxLayout()
        
        create_group_btn = QPushButton("РІС›вЂў Р РЋР С•Р В·Р Т‘Р В°РЎвЂљРЎРЉ")
        create_group_btn.setToolTip("Р РЋР С•Р В·Р Т‘Р В°РЎвЂљРЎРЉ Р Р…Р С•Р Р†РЎС“РЎР‹ Р С–РЎР‚РЎС“Р С—Р С—РЎС“")
        create_group_btn.clicked.connect(self._create_group_in_tree)
        groups_actions.addWidget(create_group_btn)
        
        rename_group_btn = QPushButton("РІСљРЏРїС‘РЏ Р СџР ВµРЎР‚Р ВµР С‘Р СР ВµР Р…Р С•Р Р†Р В°РЎвЂљРЎРЉ")
        rename_group_btn.setToolTip("Р СџР ВµРЎР‚Р ВµР С‘Р СР ВµР Р…Р С•Р Р†Р В°РЎвЂљРЎРЉ Р С–РЎР‚РЎС“Р С—Р С—РЎС“")
        rename_group_btn.clicked.connect(self._rename_group)
        groups_actions.addWidget(rename_group_btn)
        
        delete_group_btn = QPushButton("СЂСџвЂ”вЂРїС‘РЏ Р Р€Р Т‘Р В°Р В»Р С‘РЎвЂљРЎРЉ")
        delete_group_btn.setToolTip("Р Р€Р Т‘Р В°Р В»Р С‘РЎвЂљРЎРЉ Р С–РЎР‚РЎС“Р С—Р С—РЎС“")
        delete_group_btn.clicked.connect(self._delete_group_from_tree)
        groups_actions.addWidget(delete_group_btn)
        
        groups_actions.addStretch()
        
        layout.addLayout(groups_actions)
    
    def _filter_groups(self, text: str):
        """Р В¤Р С‘Р В»РЎРЉРЎвЂљРЎР‚Р С•Р Р†Р В°РЎвЂљРЎРЉ Р С–РЎР‚РЎС“Р С—Р С—РЎвЂ№ Р С—Р С• Р С—Р С•Р С‘РЎРѓР С”Р С•Р Р†Р С•Р СРЎС“ Р В·Р В°Р С—РЎР‚Р С•РЎРѓРЎС“"""
        text = text.lower().strip()
        
        # Р В¤Р С‘Р В»РЎРЉРЎвЂљРЎР‚РЎС“Р ВµР С Р Т‘Р ВµРЎР‚Р ВµР Р†Р С•
        root = self.groups_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            group_name = item.text(0).lower()
            
            # Р СџР С•Р С”Р В°Р В·РЎвЂ№Р Р†Р В°Р ВµР С/РЎРѓР С”РЎР‚РЎвЂ№Р Р†Р В°Р ВµР С Р Р† Р В·Р В°Р Р†Р С‘РЎРѓР С‘Р СР С•РЎРѓРЎвЂљР С‘ Р С•РЎвЂљ Р С—Р С•Р С‘РЎРѓР С”Р В°
            if not text or text in group_name:
                item.setHidden(False)
            else:
                item.setHidden(True)
    
    def clear(self):
        """Р С›РЎвЂЎР С‘РЎРѓРЎвЂљР С‘РЎвЂљРЎРЉ Р С—Р В°Р Р…Р ВµР В»РЎРЉ"""
        self.groups_list.clear()
        self._groups = {}
        self._render_groups()  # Р СџР ВµРЎР‚Р ВµРЎР‚Р С‘РЎРѓР С•Р Р†Р В°РЎвЂљРЎРЉ (РЎРѓ Р С™Р С•РЎР‚Р В·Р С‘Р Р…Р С•Р в„–)
    
    # === Р СљР вЂўР СћР С›Р вЂќР В« Р вЂќР вЂєР Р‡ Р вЂ™Р С™Р вЂєР С’Р вЂќР С™Р В "Р вЂњР В Р Р€Р СџР СџР В«" (РЎвЂћР В°Р в„–Р В» 45) ===
    
    def load_groups(self, groups: dict):
        """
        Р вЂ”Р В°Р С–РЎР‚РЎС“Р В·Р С‘РЎвЂљРЎРЉ Р С–РЎР‚РЎС“Р С—Р С—РЎвЂ№ Р Р† Р Т‘Р ВµРЎР‚Р ВµР Р†Р С•
        
        Args:
            groups: {group_name: [phrases]} Р С‘Р В»Р С‘ {cluster_id: {'name': str, 'phrases': [...]}}
        """
        self._groups = groups
        self._render_groups()
    
    def _render_groups(self):
        """Р С›РЎвЂљРЎР‚Р С‘РЎРѓР С•Р Р†Р В°РЎвЂљРЎРЉ Р вЂќР вЂўР В Р вЂўР вЂ™Р С› Р С–РЎР‚РЎС“Р С—Р С— РЎРѓ РЎвЂћРЎР‚Р В°Р В·Р В°Р СР С‘ (Р С”Р В°Р С” Р Р† Key Collector!)"""
        self.groups_tree.clear()
        
        # Р вЂќР С•Р В±Р В°Р Р†Р В»РЎРЏР ВµР С "Р С™Р С•РЎР‚Р В·Р С‘Р Р…Р В° (0)" Р С—Р ВµРЎР‚Р Р†Р С•Р в„– (Р С”Р В°Р С” Р Р† Key Collector)
        trash = QTreeWidgetItem(["Р С™Р С•РЎР‚Р В·Р С‘Р Р…Р В° (0)", ""])
        trash.setForeground(0, QColor("#999"))
        self.groups_tree.addTopLevelItem(trash)
        
        for group_name, data in self._groups.items():
            # Р СџР С•Р Т‘Р Т‘Р ВµРЎР‚Р В¶Р С”Р В° Р Т‘Р Р†РЎС“РЎвЂ¦ РЎвЂћР С•РЎР‚Р СР В°РЎвЂљР С•Р Р†
            if isinstance(data, dict):
                name = data.get('name', str(group_name))
                phrases = data.get('phrases', [])
            else:
                name = str(group_name)
                phrases = data if isinstance(data, list) else []
            
            # Р В¤Р С•РЎР‚Р СР В°РЎвЂљ: "Р Р…Р В°Р В·Р Р†Р В°Р Р…Р С‘Р Вµ (Р С”Р С•Р В»Р С‘РЎвЂЎР ВµРЎРѓРЎвЂљР Р†Р С•)"
            count = len(phrases)
            
            # Р РЋР С•Р В·Р Т‘Р В°Р ВµР С Р С”Р С•РЎР‚Р Р…Р ВµР Р†Р С•Р в„– РЎРЊР В»Р ВµР СР ВµР Р…РЎвЂљ Р С–РЎР‚РЎС“Р С—Р С—РЎвЂ№
            group_item = QTreeWidgetItem([f"{name} ({count})", ""])
            
            # Р СџРЎР‚Р С‘Р СР ВµР Р…РЎРЏР ВµР С РЎРѓРЎвЂљР С‘Р В»РЎРЉ Р С” Р С–РЎР‚РЎС“Р С—Р С—Р Вµ
            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)
            
            # Р В¦Р Р†Р ВµРЎвЂљ Р С—Р С• РЎС“Р СР С•Р В»РЎвЂЎР В°Р Р…Р С‘РЎР‹ Р Т‘Р В»РЎРЏ Р С–РЎР‚РЎС“Р С—Р С—РЎвЂ№
            group_color = data.get('color') if isinstance(data, dict) else None
            if group_color:
                group_item.setBackground(0, QColor(group_color))
            
            if count == 0:
                group_item.setForeground(0, QColor("#999"))
            
            # Р вЂќР С•Р В±Р В°Р Р†Р В»РЎРЏР ВµР С РЎвЂћРЎР‚Р В°Р В·РЎвЂ№ Р С”Р В°Р С” Р Т‘Р С•РЎвЂЎР ВµРЎР‚Р Р…Р С‘Р Вµ РЎРЊР В»Р ВµР СР ВµР Р…РЎвЂљРЎвЂ№
            for phrase_data in phrases:
                phrase_text = phrase_data.get("phrase", phrase_data) if isinstance(phrase_data, dict) else phrase_data
                
                # Р РЋР С•Р В·Р Т‘Р В°Р ВµР С РЎРЊР В»Р ВµР СР ВµР Р…РЎвЂљ РЎвЂћРЎР‚Р В°Р В·РЎвЂ№
                phrase_item = QTreeWidgetItem([phrase_text, ""])
                phrase_item.setForeground(0, QColor("#ddd"))
                
                group_item.addChild(phrase_item)
            
            self.groups_tree.addTopLevelItem(group_item)
        
        # Р В Р В°РЎРѓР С”РЎР‚РЎвЂ№Р Р†Р В°Р ВµР С Р Р†РЎРѓР Вµ Р С–РЎР‚РЎС“Р С—Р С—РЎвЂ№ Р С—Р С• РЎС“Р СР С•Р В»РЎвЂЎР В°Р Р…Р С‘РЎР‹
        self.groups_tree.expandAll()
    
    def _groups_context_menu(self, pos: QPoint):
        """Р С™Р С•Р Р…РЎвЂљР ВµР С”РЎРѓРЎвЂљР Р…Р С•Р Вµ Р СР ВµР Р…РЎР‹ Р Р…Р В° Р Т‘Р ВµРЎР‚Р ВµР Р†Р Вµ Р С–РЎР‚РЎС“Р С—Р С—"""
        menu = QMenu(self)
        
        item = self.groups_tree.itemAt(pos)
        
        # Р РЋР С•Р В·Р Т‘Р В°РЎвЂљРЎРЉ Р С–РЎР‚РЎС“Р С—Р С—РЎС“
        create_action = QAction("РІС›вЂў Р РЋР С•Р В·Р Т‘Р В°РЎвЂљРЎРЉ Р С–РЎР‚РЎС“Р С—Р С—РЎС“", self)
        create_action.triggered.connect(self._create_group_in_tree)
        menu.addAction(create_action)
        
        if item and not item.parent():  # Р СћР С•Р В»РЎРЉР С”Р С• Р Т‘Р В»РЎРЏ Р С–РЎР‚РЎС“Р С—Р С—, Р Р…Р Вµ Р Т‘Р В»РЎРЏ РЎвЂћРЎР‚Р В°Р В·
            menu.addSeparator()
            
            # Р СџР ВµРЎР‚Р ВµР С‘Р СР ВµР Р…Р С•Р Р†Р В°РЎвЂљРЎРЉ
            rename_action = QAction("РІСљРЏРїС‘РЏ Р СџР ВµРЎР‚Р ВµР С‘Р СР ВµР Р…Р С•Р Р†Р В°РЎвЂљРЎРЉ", self)
            rename_action.triggered.connect(self._rename_group)
            menu.addAction(rename_action)
            
            # Р СњР В°Р В·Р Р…Р В°РЎвЂЎР С‘РЎвЂљРЎРЉ РЎвЂ Р Р†Р ВµРЎвЂљ (Р С”Р В°Р С” Р Р† Key Collector!)
            color_menu = QMenu("СЂСџР‹РЃ Р СњР В°Р В·Р Р…Р В°РЎвЂЎР С‘РЎвЂљРЎРЉ РЎвЂ Р Р†Р ВµРЎвЂљ", self)
            
            # Р СџРЎР‚Р ВµР Т‘РЎС“РЎРѓРЎвЂљР В°Р Р…Р С•Р Р†Р В»Р ВµР Р…Р Р…РЎвЂ№Р Вµ РЎвЂ Р Р†Р ВµРЎвЂљР В°
            colors = [
                ("#FFD700", "Р вЂ“Р ВµР В»РЎвЂљРЎвЂ№Р в„–"),
                ("#90EE90", "Р вЂ”Р ВµР В»Р ВµР Р…РЎвЂ№Р в„–"),
                ("#87CEEB", "Р вЂњР С•Р В»РЎС“Р В±Р С•Р в„–"),
                ("#FFA500", "Р С›РЎР‚Р В°Р Р…Р В¶Р ВµР Р†РЎвЂ№Р в„–"),
                ("#FF69B4", "Р В Р С•Р В·Р С•Р Р†РЎвЂ№Р в„–"),
                ("#DDA0DD", "Р РЋР С‘РЎР‚Р ВµР Р…Р ВµР Р†РЎвЂ№Р в„–"),
                ("#F0E68C", "Р вЂР ВµР В¶Р ВµР Р†РЎвЂ№Р в„–"),
                ("", "Р вЂР ВµР В· РЎвЂ Р Р†Р ВµРЎвЂљР В°")
            ]
            
            for color_code, color_name in colors:
                color_action = QAction(color_name, self)
                if color_code:
                    # Р СџР С•Р С”Р В°Р В·РЎвЂ№Р Р†Р В°Р ВµР С РЎвЂ Р Р†Р ВµРЎвЂљ Р Р† Р С‘Р С”Р С•Р Р…Р С”Р Вµ
                    from PySide6.QtGui import QPixmap, QPainter
                    pixmap = QPixmap(16, 16)
                    pixmap.fill(QColor(color_code))
                    color_action.setIcon(QIcon(pixmap))
                color_action.triggered.connect(lambda checked, c=color_code: self._set_group_color(c))
                color_menu.addAction(color_action)
            
            menu.addMenu(color_menu)
            
            menu.addSeparator()
            
            # Р Р€Р Т‘Р В°Р В»Р С‘РЎвЂљРЎРЉ
            delete_action = QAction("СЂСџвЂ”вЂРїС‘РЏ Р Р€Р Т‘Р В°Р В»Р С‘РЎвЂљРЎРЉ Р С–РЎР‚РЎС“Р С—Р С—РЎС“", self)
            delete_action.triggered.connect(self._delete_group_from_tree)
            menu.addAction(delete_action)
            
            menu.addSeparator()
                
            # Экспорт группы
            export_action = QAction("📥 Экспортировать группу", self)
            export_action.triggered.connect(lambda: self._export_group(item))
            menu.addAction(export_action)
        
        menu.exec(self.groups_list.mapToGlobal(pos))
    
    def _create_group_in_tree(self):
        """Р РЋР С•Р В·Р Т‘Р В°РЎвЂљРЎРЉ Р Р…Р С•Р Р†РЎС“РЎР‹ Р С–РЎР‚РЎС“Р С—Р С—РЎС“"""
        name, ok = QInputDialog.getText(
            self,
            "Р СњР С•Р Р†Р В°РЎРЏ Р С–РЎР‚РЎС“Р С—Р С—Р В°",
            "Р СњР В°Р В·Р Р†Р В°Р Р…Р С‘Р Вµ Р С–РЎР‚РЎС“Р С—Р С—РЎвЂ№:"
        )
        
        if ok and name.strip():
            name = name.strip()
            if name in self._groups:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Р С›РЎв‚¬Р С‘Р В±Р С”Р В°", f"Р вЂњРЎР‚РЎС“Р С—Р С—Р В° '{name}' РЎС“Р В¶Р Вµ РЎРѓРЎС“РЎвЂ°Р ВµРЎРѓРЎвЂљР Р†РЎС“Р ВµРЎвЂљ")
                return
            
            # Р РЋР С•Р В·Р Т‘Р В°Р ВµР С Р С—РЎС“РЎРѓРЎвЂљРЎС“РЎР‹ Р С–РЎР‚РЎС“Р С—Р С—РЎС“
            self._groups[name] = []
            self._render_groups()
            
            print(f"[OK] Р РЋР С•Р В·Р Т‘Р В°Р Р…Р В° Р С–РЎР‚РЎС“Р С—Р С—Р В°: {name}")
    
    def _rename_group(self):
        """Р СџР ВµРЎР‚Р ВµР С‘Р СР ВµР Р…Р С•Р Р†Р В°РЎвЂљРЎРЉ Р Р†РЎвЂ№Р В±РЎР‚Р В°Р Р…Р Р…РЎС“РЎР‹ Р С–РЎР‚РЎС“Р С—Р С—РЎС“"""
        item = self.groups_tree.currentItem()
        if not item or item.parent():  # Р ВР С–Р Р…Р С•РЎР‚Р С‘РЎР‚РЎС“Р ВµР С Р ВµРЎРѓР В»Р С‘ РЎРЊРЎвЂљР С• РЎвЂћРЎР‚Р В°Р В·Р В°, Р В° Р Р…Р Вµ Р С–РЎР‚РЎС“Р С—Р С—Р В°
            return
        
        old_name = item.text(0).split(" (")[0]  # Р Р€Р В±Р С‘РЎР‚Р В°Р ВµР С РЎРѓРЎвЂЎР ВµРЎвЂљРЎвЂЎР С‘Р С”
        new_name, ok = QInputDialog.getText(
            self,
            "Р СџР ВµРЎР‚Р ВµР С‘Р СР ВµР Р…Р С•Р Р†Р В°РЎвЂљРЎРЉ Р С–РЎР‚РЎС“Р С—Р С—РЎС“",
            "Р СњР С•Р Р†Р С•Р Вµ Р Р…Р В°Р В·Р Р†Р В°Р Р…Р С‘Р Вµ:",
            text=old_name
        )
        
        if ok and new_name.strip() and new_name != old_name:
            new_name = new_name.strip()
            
            if new_name in self._groups:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Р С›РЎв‚¬Р С‘Р В±Р С”Р В°", f"Р вЂњРЎР‚РЎС“Р С—Р С—Р В° '{new_name}' РЎС“Р В¶Р Вµ РЎРѓРЎС“РЎвЂ°Р ВµРЎРѓРЎвЂљР Р†РЎС“Р ВµРЎвЂљ")
                return
            
            # Р СџР ВµРЎР‚Р ВµР С‘Р СР ВµР Р…Р С•Р Р†РЎвЂ№Р Р†Р В°Р ВµР С
            self._groups[new_name] = self._groups.pop(old_name)
            self._render_groups()
            
            print(f"[OK] Р вЂњРЎР‚РЎС“Р С—Р С—Р В° Р С—Р ВµРЎР‚Р ВµР С‘Р СР ВµР Р…Р С•Р Р†Р В°Р Р…Р В°: {old_name} РІвЂ вЂ™ {new_name}")
    
    def _delete_group_from_tree(self):
        """Р Р€Р Т‘Р В°Р В»Р С‘РЎвЂљРЎРЉ Р Р†РЎвЂ№Р В±РЎР‚Р В°Р Р…Р Р…РЎС“РЎР‹ Р С–РЎР‚РЎС“Р С—Р С—РЎС“"""
        item = self.groups_tree.currentItem()
        if not item or item.parent():  # Р ВР С–Р Р…Р С•РЎР‚Р С‘РЎР‚РЎС“Р ВµР С Р ВµРЎРѓР В»Р С‘ РЎРЊРЎвЂљР С• РЎвЂћРЎР‚Р В°Р В·Р В°
            return
        
        group_name = item.text(0).split(" (")[0]
        phrases_count = item.childCount()
        
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Р Р€Р Т‘Р В°Р В»Р С‘РЎвЂљРЎРЉ Р С–РЎР‚РЎС“Р С—Р С—РЎС“",
            f"Р Р€Р Т‘Р В°Р В»Р С‘РЎвЂљРЎРЉ Р С–РЎР‚РЎС“Р С—Р С—РЎС“ '{group_name}' ({phrases_count} РЎвЂћРЎР‚Р В°Р В·)?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if group_name in self._groups:
                del self._groups[group_name]
                self._render_groups()
                print(f"[OK] Р вЂњРЎР‚РЎС“Р С—Р С—Р В° РЎС“Р Т‘Р В°Р В»Р ВµР Р…Р В°: {group_name}")
    
    def _export_group(self, item: QTreeWidgetItem):
        """Р В­Р С”РЎРѓР С—Р С•РЎР‚РЎвЂљР С‘РЎР‚Р С•Р Р†Р В°РЎвЂљРЎРЉ Р С–РЎР‚РЎС“Р С—Р С—РЎС“ Р Р† CSV"""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from pathlib import Path
        import csv
        
        group_name = item.text(0)
        phrases = self._groups.get(group_name, [])
        
        if isinstance(phrases, dict):
            phrases = phrases.get('phrases', [])
        
        if not phrases:
            QMessageBox.warning(self, "Р В­Р С”РЎРѓР С—Р С•РЎР‚РЎвЂљ", "Р вЂњРЎР‚РЎС“Р С—Р С—Р В° Р С—РЎС“РЎРѓРЎвЂљР В°")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Р В­Р С”РЎРѓР С—Р С•РЎР‚РЎвЂљ Р С–РЎР‚РЎС“Р С—Р С—РЎвЂ№",
            str(Path.home() / f"{group_name}.csv"),
            "CSV files (*.csv)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Р В¤РЎР‚Р В°Р В·Р В°'])
                    for phrase in phrases:
                        writer.writerow([str(phrase)])
                
                QMessageBox.information(
                    self,
                    "Р В­Р С”РЎРѓР С—Р С•РЎР‚РЎвЂљ",
                    f"Р В­Р С”РЎРѓР С—Р С•РЎР‚РЎвЂљР С‘РЎР‚Р С•Р Р†Р В°Р Р…Р С• {len(phrases)} РЎвЂћРЎР‚Р В°Р В· Р С‘Р В· Р С–РЎР‚РЎС“Р С—Р С—РЎвЂ№ '{group_name}'"
                )
            except Exception as e:
                QMessageBox.warning(self, "Р С›РЎв‚¬Р С‘Р В±Р С”Р В° РЎРЊР С”РЎРѓР С—Р С•РЎР‚РЎвЂљР В°", str(e))

    def _set_group_color(self, color_code: str):
        """Р СњР В°Р В·Р Р…Р В°РЎвЂЎР С‘РЎвЂљРЎРЉ РЎвЂ Р Р†Р ВµРЎвЂљ Р С–РЎР‚РЎС“Р С—Р С—Р Вµ (Р С”Р В°Р С” Р Р† Key Collector)"""
        item = self.groups_tree.currentItem()
        if not item or item.parent():  # Р СћР С•Р В»РЎРЉР С”Р С• Р Т‘Р В»РЎРЏ Р С–РЎР‚РЎС“Р С—Р С—
            return
        
        group_name = item.text(0).split(" (")[0]
        
        # Р СџРЎР‚Р С‘Р СР ВµР Р…РЎРЏР ВµР С РЎвЂ Р Р†Р ВµРЎвЂљ
        if color_code:
            item.setBackground(0, QColor(color_code))
            # Р РЋР С•РЎвЂ¦РЎР‚Р В°Р Р…РЎРЏР ВµР С Р Р† Р Т‘Р В°Р Р…Р Р…РЎвЂ№РЎвЂ¦ Р С–РЎР‚РЎС“Р С—Р С—РЎвЂ№
            if group_name in self._groups:
                if isinstance(self._groups[group_name], dict):
                    self._groups[group_name]['color'] = color_code
                else:
                    # Р С™Р С•Р Р…Р Р†Р ВµРЎР‚РЎвЂљР С‘РЎР‚РЎС“Р ВµР С Р Р† dict РЎвЂћР С•РЎР‚Р СР В°РЎвЂљ
                    self._groups[group_name] = {
                        'name': group_name,
                        'phrases': self._groups[group_name],
                        'color': color_code
                    }
        else:
            # Р Р€Р В±Р С‘РЎР‚Р В°Р ВµР С РЎвЂ Р Р†Р ВµРЎвЂљ
            item.setBackground(0, QColor("transparent"))
            if group_name in self._groups and isinstance(self._groups[group_name], dict):
                self._groups[group_name].pop('color', None)
        
        print(f"[OK] Р В¦Р Р†Р ВµРЎвЂљ Р С–РЎР‚РЎС“Р С—Р С—РЎвЂ№ '{group_name}' Р С‘Р В·Р СР ВµР Р…Р ВµР Р… Р Р…Р В° {color_code or 'Р В±Р ВµР В· РЎвЂ Р Р†Р ВµРЎвЂљР В°'}")



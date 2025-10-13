"""
Модуль для работы с иконками Яндекс (файл 44 + yandex-icon-pack-v1)
Предоставляет удобный доступ к SVG иконкам с правильными размерами
"""
from pathlib import Path
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QSize
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPainter, QImage

class YandexIcons:
    """Класс для работы с иконками Яндекс дизайн-системы"""
    
    # Путь к папке с иконками
    ICONS_DIR = Path(__file__).parent.parent / "assets" / "icons"
    
    # Карта иконок (из файла 44)
    ICONS = {
        # Браузеры и сессии
        "browser": "browser.svg",
        "activity": "activity.svg",
        "layers": "layers.svg",
        "shield": "shield.svg",
        "globe_lock": "globe-lock.svg",
        
        # Действия
        "refresh": "refresh-ccw.svg",
        "search": "search.svg",
        "download": "download.svg",
        "upload": "file-down.svg",
        "paste": "clipboard-paste.svg",
        
        # Статусы
        "check": "check-circle-2.svg",
        "target": "target.svg",
        
        # Разделы приложения
        "users": "users.svg",
        "history": "history.svg",
        "settings": "settings.svg",
        "server": "server.svg",
        "zap": "zap-fast.svg",
        "chart": "bar-chart-vertical.svg",
        "list": "list-checks.svg",
    }
    
    # Размеры по спецификации (файл 44)
    SIZE_S = QSize(18, 18)   # Маленькие (редко)
    SIZE_M = QSize(20, 20)   # Кнопки (Button M)
    SIZE_L = QSize(24, 24)   # Toolbar, IconButton
    
    @classmethod
    def get_icon(cls, name: str, size: QSize = None) -> QIcon:
        """
        Получить QIcon по имени
        
        Args:
            name: Имя иконки из карты ICONS
            size: Размер иконки (по умолчанию SIZE_L)
        
        Returns:
            QIcon с SVG иконкой
        """
        if size is None:
            size = cls.SIZE_L
        
        icon_file = cls.ICONS.get(name)
        if not icon_file:
            print(f"[WARN] Иконка '{name}' не найдена в карте")
            return QIcon()
        
        icon_path = cls.ICONS_DIR / icon_file
        if not icon_path.exists():
            print(f"[WARN] Файл иконки не найден: {icon_path}")
            return QIcon()
        
        return QIcon(str(icon_path))
    
    @classmethod
    def get_pixmap(cls, name: str, size: QSize = None, color: str = None) -> QPixmap:
        """
        Получить QPixmap с возможностью перекраски (currentColor из файла 44)
        
        Args:
            name: Имя иконки
            size: Размер
            color: Цвет для перекраски (например "#FFB300")
        
        Returns:
            QPixmap с иконкой
        """
        if size is None:
            size = cls.SIZE_L
        
        icon_file = cls.ICONS.get(name)
        if not icon_file:
            return QPixmap()
        
        icon_path = cls.ICONS_DIR / icon_file
        if not icon_path.exists():
            return QPixmap()
        
        # Рендерим SVG в нужный размер
        renderer = QSvgRenderer(str(icon_path))
        image = QImage(size.width(), size.height(), QImage.Format_ARGB32)
        image.fill(0)  # Прозрачный фон
        
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        
        return QPixmap.fromImage(image)


# Удобные алиасы для быстрого доступа
def icon(name: str, size: str = "L") -> QIcon:
    """
    Быстрый доступ к иконке
    
    Args:
        name: Имя иконки
        size: "S" (18x18), "M" (20x20) или "L" (24x24)
    
    Returns:
        QIcon
    
    Example:
        btn.setIcon(icon("refresh", "L"))
    """
    size_map = {
        "S": YandexIcons.SIZE_S,
        "M": YandexIcons.SIZE_M,
        "L": YandexIcons.SIZE_L,
    }
    return YandexIcons.get_icon(name, size_map.get(size, YandexIcons.SIZE_L))

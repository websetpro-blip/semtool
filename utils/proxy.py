"""
Утилиты для работы с прокси
Парсинг строк прокси в формат Playwright
"""

from urllib.parse import urlparse
from typing import Optional, Dict


def parse_proxy(proxy_str: Optional[str]) -> Optional[Dict[str, str]]:
    """
    Парсит строку прокси в формат Playwright API
    
    Поддерживаемые форматы:
    - ip:port
    - user:pass@ip:port
    - http://user:pass@ip:port
    - https://user:pass@ip:port
    - socks5://user:pass@ip:port
    
    Returns:
        {
            "server": "http://ip:port",
            "username": "user" (optional),
            "password": "pass" (optional)
        }
    """
    if not proxy_str:
        return None
    
    proxy_str = proxy_str.strip()
    if not proxy_str:
        return None
    
    # Добавляем схему если нет
    if "://" not in proxy_str:
        proxy_str = "http://" + proxy_str
    
    try:
        parsed = urlparse(proxy_str)
        
        if not parsed.hostname or not parsed.port:
            return None
        
        result = {
            "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
        }
        
        # Добавляем username/password если есть
        if parsed.username:
            result["username"] = parsed.username
        
        if parsed.password:
            result["password"] = parsed.password
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Не удалось распарсить прокси '{proxy_str}': {e}")
        return None

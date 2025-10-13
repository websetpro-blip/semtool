"""
Парсинг прокси строки в формат для Playwright
Поддерживает форматы:
- ip:port@user:pass
- user:pass@ip:port  
- http://user:pass@ip:port
"""

from urllib.parse import urlparse
from typing import Optional, Dict


def parse_proxy(proxy_str: str) -> Optional[Dict[str, str]]:
    """
    Парсит прокси строку в формат для Playwright
    
    Args:
        proxy_str: Строка прокси в любом формате
    
    Returns:
        {
            "server": "http://ip:port",
            "username": "user",
            "password": "pass"
        }
        или None если прокси не указан
    """
    if not proxy_str:
        return None
    
    proxy_str = proxy_str.strip()
    
    # Формат: ip:port@user:pass (SemTool стандарт)
    if '@' in proxy_str and not proxy_str.startswith('http'):
        parts = proxy_str.split('@', 1)
        if len(parts) == 2:
            server_part = parts[0]  # ip:port
            auth_part = parts[1]     # user:pass
            
            if ':' in auth_part:
                username, password = auth_part.split(':', 1)
                return {
                    "server": f"http://{server_part}",
                    "username": username,
                    "password": password
                }
            else:
                # Без пароля
                return {
                    "server": f"http://{server_part}",
                    "username": auth_part,
                    "password": ""
                }
    
    # Формат с протоколом: http://user:pass@ip:port
    if '://' in proxy_str:
        try:
            parsed = urlparse(proxy_str)
            host = parsed.hostname
            port = parsed.port or 8080
            username = parsed.username or ""
            password = parsed.password or ""
            scheme = parsed.scheme or "http"
            
            result = {
                "server": f"{scheme}://{host}:{port}",
            }
            
            if username:
                result["username"] = username
                result["password"] = password
            
            return result
        except:
            pass
    
    # Формат без авторизации: ip:port
    if ':' in proxy_str:
        return {
            "server": f"http://{proxy_str}"
        }
    
    return None


def test_parse():
    """Тесты парсинга"""
    test_cases = [
        "213.139.221.13:9620@Nuj2eh:M6FEcS",
        "http://Nuj2eh:M6FEcS@213.139.221.13:9620",
        "192.168.1.1:8080",
        None,
        ""
    ]
    
    for test in test_cases:
        result = parse_proxy(test)
        print(f"Input: {test}")
        print(f"Result: {result}")
        print()


if __name__ == "__main__":
    test_parse()

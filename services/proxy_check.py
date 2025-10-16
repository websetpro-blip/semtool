"""
Сервис проверки прокси
Проверяет доступность и скорость прокси через Yandex
"""

import aiohttp
import asyncio
import time
from typing import Optional, Dict, Any


async def test_proxy(proxy_url: Optional[str], timeout: int = 10) -> Dict[str, Any]:
    """
    Проверка прокси через http://httpbin.org/ip (правильный метод без ssl:default ошибок)
    
    Args:
        proxy_url: URL прокси в формате:
            - ip:port@user:pass (KeySet формат)
            - http://user:pass@ip:port (стандартный URL)
            - socks5://user:pass@ip:port (SOCKS прокси)
        timeout: Таймаут в секундах
    
    Returns:
        {
            "ok": bool,
            "ip": str,  # Внешний IP
            "latency_ms": int,  # Задержка в миллисекундах
            "error": str  # Текст ошибки если ok=False
        }
    """
    if not proxy_url:
        return {
            "ok": False,
            "ip": None,
            "latency_ms": 0,
            "error": "Прокси не указан"
        }
    
    start_time = time.time()
    
    try:
        # Парсим прокси в правильный формат для aiohttp
        proxy_auth = None
        is_socks = False
        
        # Формат: ip:port@user:pass (из KeySet)
        if '@' in proxy_url and not proxy_url.startswith('http') and not proxy_url.startswith('socks'):
            parts = proxy_url.split('@')
            if len(parts) == 2:
                host_port = parts[0]
                user_pass = parts[1]
                user, password = user_pass.split(':', 1)
                proxy_url_clean = f"http://{host_port}"
                proxy_auth = aiohttp.BasicAuth(user, password)
            else:
                proxy_url_clean = f"http://{proxy_url}"
        # Формат: http://user:pass@ip:port
        elif '@' in proxy_url and '://' in proxy_url:
            import re
            if proxy_url.startswith('socks'):
                # SOCKS прокси - нужен ProxyConnector (пока возвращаем ошибку)
                is_socks = True
                proxy_url_clean = proxy_url
            else:
                match = re.match(r'(https?://)([^:]+):([^@]+)@(.+)', proxy_url)
                if match:
                    protocol, user, password, host_port = match.groups()
                    proxy_url_clean = f"{protocol}{host_port}"
                    proxy_auth = aiohttp.BasicAuth(user, password)
                else:
                    proxy_url_clean = proxy_url
        else:
            # Без авторизации
            if proxy_url.startswith('socks'):
                is_socks = True
                proxy_url_clean = proxy_url
            elif not proxy_url.startswith('http'):
                proxy_url_clean = f"http://{proxy_url}"
            else:
                proxy_url_clean = proxy_url
        
        # SOCKS прокси требуют aiohttp_socks
        if is_socks:
            try:
                from aiohttp_socks import ProxyConnector
                # Парсим SOCKS URL
                import re
                match = re.match(r'socks[45]?://(?:([^:]+):([^@]+)@)?(.+)', proxy_url)
                if match:
                    user, password, host_port = match.groups()
                    conn = ProxyConnector.from_url(
                        proxy_url,
                        rdns=True,
                        username=user or None,
                        password=password or None
                    )
                    
                    timeout_obj = aiohttp.ClientTimeout(total=timeout)
                    async with aiohttp.ClientSession(connector=conn, timeout=timeout_obj) as session:
                        async with session.get("http://httpbin.org/ip") as response:
                            data = await response.json()
                            latency_ms = int((time.time() - start_time) * 1000)
                            return {
                                "ok": True,
                                "ip": data.get("origin", "ok"),
                                "latency_ms": latency_ms,
                                "error": None
                            }
            except ImportError:
                return {
                    "ok": False,
                    "ip": None,
                    "latency_ms": 0,
                    "error": "aiohttp_socks не установлен для SOCKS прокси"
                }
        
        # HTTP/HTTPS прокси - используем httpbin.org/ip с ssl=False
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(
            timeout=timeout_obj,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        ) as session:
            async with session.get(
                "http://httpbin.org/ip",  # HTTP вместо HTTPS - избегаем ssl:default ошибок
                proxy=proxy_url_clean,
                proxy_auth=proxy_auth,
                ssl=False  # Важно для HTTP прокси
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                return {
                    "ok": True,
                    "ip": data.get("origin", "ok"),
                    "latency_ms": latency_ms,
                    "error": None
                }
    
    except asyncio.TimeoutError:
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "ok": False,
            "ip": None,
            "latency_ms": latency_ms,
            "error": f"Timeout {timeout}s"
        }
    
    except aiohttp.ClientProxyConnectionError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "ok": False,
            "ip": None,
            "latency_ms": latency_ms,
            "error": f"Proxy error: {str(e)}"
        }
    
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "ok": False,
            "ip": None,
            "latency_ms": latency_ms,
            "error": str(e)
        }


async def test_multiple_proxies(proxies: list[str], timeout: int = 10) -> Dict[str, Dict[str, Any]]:
    """
    Проверка нескольких прокси параллельно
    
    Args:
        proxies: Список прокси URL
        timeout: Таймаут для каждого прокси
    
    Returns:
        {proxy_url: result_dict}
    """
    tasks = [test_proxy(proxy, timeout) for proxy in proxies]
    results = await asyncio.gather(*tasks)
    
    return {proxy: result for proxy, result in zip(proxies, results)}


def format_proxy_url(host: str, port: int, user: str, password: str, protocol: str = "http") -> str:
    """
    Форматирование URL прокси
    
    Args:
        host: IP или домен
        port: Порт
        user: Логин
        password: Пароль
        protocol: Протокол (http/https/socks5)
    
    Returns:
        Отформатированный URL: protocol://user:pass@host:port
    """
    return f"{protocol}://{user}:{password}@{host}:{port}"


# Тестирование (если запустить напрямую)
if __name__ == "__main__":
    # Тестовые прокси из файла
    test_proxies = [
        "http://Nuj2eh:M6FEcS@213.139.221.13:9620",
        "http://Nuj2eh:M6FEcS@213.139.223.16:9739",
        "http://Nuj2eh:M6FEcS@213.139.221.165:9041",
        "http://Nuj2eh:M6FEcS@213.139.223.21:9373",
    ]
    
    async def run_test():
        print("Проверка прокси...")
        results = await test_multiple_proxies(test_proxies)
        
        for proxy, result in results.items():
            status = "[OK]" if result["ok"] else "[FAIL]"
            print(f"{status} {proxy}")
            print(f"  IP: {result['ip']}")
            print(f"  Latency: {result['latency_ms']}ms")
            if result["error"]:
                print(f"  Error: {result['error']}")
            print()
    
    asyncio.run(run_test())

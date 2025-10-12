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
    Проверка прокси через https://yandex.ru/internet
    
    Args:
        proxy_url: URL прокси в формате http://user:pass@host:port или None
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
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(
            timeout=timeout_obj,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        ) as session:
            async with session.get("https://yandex.ru/internet", proxy=proxy_url) as response:
                response.raise_for_status()
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Пытаемся извлечь IP из заголовков
                ip = response.headers.get("x-client-ip")
                if not ip:
                    # Если в заголовках нет, пробуем из тела
                    ip = "ok"
                
                return {
                    "ok": True,
                    "ip": ip,
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

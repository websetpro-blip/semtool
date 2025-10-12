"""
Сервис для работы с капчей (RuCaptcha/CapMonster)
Проверка баланса и решение капчи
"""

import aiohttp
import asyncio
import time
from typing import Optional, Dict, Any


class RuCaptchaClient:
    """Клиент для работы с RuCaptcha API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://rucaptcha.com"
    
    async def get_balance(self) -> Dict[str, Any]:
        """
        Получить баланс аккаунта
        
        Returns:
            {
                "ok": bool,
                "balance": float,  # Баланс в рублях
                "error": str  # Текст ошибки если ok=False
            }
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                url = f"{self.base_url}/res.php"
                params = {
                    "key": self.api_key,
                    "action": "getbalance"
                }
                
                async with session.get(url, params=params) as response:
                    text = await response.text()
                    text = text.strip()
                    
                    # Проверка на ошибки
                    if text.startswith("ERROR"):
                        error_msg = text.replace("ERROR_", "").replace("_", " ")
                        return {
                            "ok": False,
                            "balance": 0.0,
                            "error": error_msg
                        }
                    
                    # Пробуем распарсить как float
                    try:
                        balance = float(text)
                        return {
                            "ok": True,
                            "balance": balance,
                            "error": None
                        }
                    except ValueError:
                        return {
                            "ok": False,
                            "balance": 0.0,
                            "error": f"Неожиданный ответ: {text}"
                        }
        
        except asyncio.TimeoutError:
            return {
                "ok": False,
                "balance": 0.0,
                "error": "Timeout 10s"
            }
        
        except Exception as e:
            return {
                "ok": False,
                "balance": 0.0,
                "error": str(e)
            }
    
    async def solve_image(self, image_base64: str, **kwargs) -> Dict[str, Any]:
        """
        Решить капчу с изображения
        
        Args:
            image_base64: Изображение в base64
            **kwargs: Дополнительные параметры (phrase, regsense, numeric и т.д.)
        
        Returns:
            {
                "ok": bool,
                "code": str,  # Текст капчи
                "captcha_id": str,  # ID капчи
                "error": str  # Текст ошибки если ok=False
            }
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                # Отправка капчи
                url = f"{self.base_url}/in.php"
                data = {
                    "key": self.api_key,
                    "method": "base64",
                    "body": image_base64,
                    "json": 1
                }
                data.update(kwargs)
                
                async with session.post(url, data=data) as response:
                    result = await response.json()
                    
                    if result.get("status") != 1:
                        return {
                            "ok": False,
                            "code": None,
                            "captcha_id": None,
                            "error": result.get("request", "Unknown error")
                        }
                    
                    captcha_id = result.get("request")
                
                # Ждем решение (макс 60 сек)
                for attempt in range(24):
                    await asyncio.sleep(2.5)
                    
                    url = f"{self.base_url}/res.php"
                    params = {
                        "key": self.api_key,
                        "action": "get",
                        "id": captcha_id,
                        "json": 1
                    }
                    
                    async with session.get(url, params=params) as response:
                        result = await response.json()
                        
                        if result.get("status") == 1:
                            return {
                                "ok": True,
                                "code": result.get("request"),
                                "captcha_id": captcha_id,
                                "error": None
                            }
                        
                        # Если еще не готово - продолжаем ждать
                        if result.get("request") == "CAPCHA_NOT_READY":
                            continue
                        
                        # Если другая ошибка
                        return {
                            "ok": False,
                            "code": None,
                            "captcha_id": captcha_id,
                            "error": result.get("request", "Unknown error")
                        }
                
                # Timeout
                return {
                    "ok": False,
                    "code": None,
                    "captcha_id": captcha_id,
                    "error": "Timeout 60s"
                }
        
        except Exception as e:
            return {
                "ok": False,
                "code": None,
                "captcha_id": None,
                "error": str(e)
            }
    
    async def report_bad(self, captcha_id: str) -> bool:
        """
        Пожаловаться на неправильное решение капчи
        
        Args:
            captcha_id: ID капчи
        
        Returns:
            True если жалоба принята
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                url = f"{self.base_url}/res.php"
                params = {
                    "key": self.api_key,
                    "action": "reportbad",
                    "id": captcha_id
                }
                
                async with session.get(url, params=params) as response:
                    text = await response.text()
                    return text.strip() == "OK_REPORT_RECORDED"
        
        except:
            return False


# Тестирование (если запустить напрямую)
if __name__ == "__main__":
    # Тестовый ключ из файла
    TEST_KEY = "8f00b4cb9b77d982abb77260a168f976"
    
    async def test():
        print("Проверка RuCaptcha...")
        client = RuCaptchaClient(TEST_KEY)
        
        # Проверка баланса
        result = await client.get_balance()
        
        if result["ok"]:
            print(f"[OK] Баланс: {result['balance']:.2f} руб")
        else:
            print(f"[FAIL] Ошибка: {result['error']}")
    
    asyncio.run(test())

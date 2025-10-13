"""
Сервис работы с капчами
Поддержка: RuCaptcha, CapMonster, 2Captcha
"""

from __future__ import annotations
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from pathlib import Path


class CaptchaService:
    """Универсальный клиент для решения капч"""
    
    def __init__(self, api_key: str, service: str = "rucaptcha"):
        """
        Args:
            api_key: API ключ сервиса
            service: rucaptcha | capmonster | 2captcha
        """
        self.api_key = api_key
        self.service = service.lower()
        
        # URL endpoints
        self.endpoints = {
            "rucaptcha": {
                "in": "https://rucaptcha.com/in.php",
                "res": "https://rucaptcha.com/res.php"
            },
            "capmonster": {
                "in": "https://api.capmonster.cloud/createTask",
                "res": "https://api.capmonster.cloud/getTaskResult"
            },
            "2captcha": {
                "in": "https://2captcha.com/in.php",
                "res": "https://2captcha.com/res.php"
            }
        }
        
        if self.service not in self.endpoints:
            raise ValueError(f"Неподдерживаемый сервис: {service}")
    
    async def get_balance(self) -> float:
        """Получить баланс на счету"""
        try:
            if self.service == "capmonster":
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.capmonster.cloud/getBalance",
                        json={"clientKey": self.api_key},
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        data = await resp.json()
                        return float(data.get("balance", 0))
            else:
                # RuCaptcha / 2Captcha
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        self.endpoints[self.service]["res"],
                        params={"key": self.api_key, "action": "getbalance"},
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        text = await resp.text()
                        return float(text.strip())
        except Exception as e:
            print(f"[Captcha] Ошибка получения баланса: {e}")
            return 0.0
    
    async def solve_image(self, image_base64: str, **kwargs) -> Optional[str]:
        """
        Решить капчу с картинки
        
        Args:
            image_base64: Изображение в base64
            **kwargs: Дополнительные параметры (numeric, min_len, max_len, etc)
        
        Returns:
            Текст капчи или None при ошибке
        """
        try:
            if self.service == "capmonster":
                return await self._solve_capmonster(image_base64, **kwargs)
            else:
                return await self._solve_rucaptcha(image_base64, **kwargs)
        except Exception as e:
            print(f"[Captcha] Ошибка решения: {e}")
            return None
    
    async def _solve_rucaptcha(self, image_base64: str, **kwargs) -> Optional[str]:
        """RuCaptcha / 2Captcha решение"""
        async with aiohttp.ClientSession() as session:
            # Отправляем капчу
            data = {
                "key": self.api_key,
                "method": "base64",
                "body": image_base64,
                "json": 1
            }
            data.update(kwargs)
            
            async with session.post(
                self.endpoints[self.service]["in"],
                data=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                result = await resp.json()
                if result.get("status") != 1:
                    print(f"[Captcha] Ошибка отправки: {result.get('request')}")
                    return None
                
                captcha_id = result["request"]
            
            # Ждем решения (до 60 секунд)
            for attempt in range(24):
                await asyncio.sleep(2.5)
                
                async with session.get(
                    self.endpoints[self.service]["res"],
                    params={
                        "key": self.api_key,
                        "action": "get",
                        "id": captcha_id,
                        "json": 1
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    result = await resp.json()
                    
                    if result.get("status") == 1:
                        return result["request"]
                    
                    if result.get("request") not in ["CAPCHA_NOT_READY", "ERROR_CAPTCHA_UNSOLVABLE"]:
                        print(f"[Captcha] Ошибка решения: {result.get('request')}")
                        return None
            
            print("[Captcha] Превышен таймаут ожидания")
            return None
    
    async def _solve_capmonster(self, image_base64: str, **kwargs) -> Optional[str]:
        """CapMonster решение"""
        async with aiohttp.ClientSession() as session:
            # Создаем задачу
            task_data = {
                "clientKey": self.api_key,
                "task": {
                    "type": "ImageToTextTask",
                    "body": image_base64
                }
            }
            
            # Добавляем параметры если есть
            if kwargs.get("numeric"):
                task_data["task"]["numeric"] = kwargs["numeric"]
            if kwargs.get("minLength"):
                task_data["task"]["minLength"] = kwargs["minLength"]
            if kwargs.get("maxLength"):
                task_data["task"]["maxLength"] = kwargs["maxLength"]
            
            async with session.post(
                self.endpoints[self.service]["in"],
                json=task_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                result = await resp.json()
                if result.get("errorId"):
                    print(f"[Captcha] Ошибка создания задачи: {result.get('errorDescription')}")
                    return None
                
                task_id = result["taskId"]
            
            # Ждем решения
            for attempt in range(24):
                await asyncio.sleep(2.5)
                
                async with session.post(
                    self.endpoints[self.service]["res"],
                    json={
                        "clientKey": self.api_key,
                        "taskId": task_id
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    result = await resp.json()
                    
                    if result.get("status") == "ready":
                        return result["solution"]["text"]
                    
                    if result.get("errorId"):
                        print(f"[Captcha] Ошибка получения результата: {result.get('errorDescription')}")
                        return None
            
            print("[Captcha] Превышен таймаут ожидания")
            return None


# Удобные функции для быстрого использования

async def check_balance(api_key: str, service: str = "rucaptcha") -> float:
    """Проверить баланс"""
    captcha = CaptchaService(api_key, service)
    return await captcha.get_balance()


async def solve_captcha(api_key: str, image_base64: str, service: str = "rucaptcha", **kwargs) -> Optional[str]:
    """Решить капчу"""
    captcha = CaptchaService(api_key, service)
    return await captcha.solve_image(image_base64, **kwargs)

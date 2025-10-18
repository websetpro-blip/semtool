"""
Единое хранилище прокси (ProxyStore)
Синхронизируется с аккаунтами, хранит статусы проверок
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import List, Dict, Optional
from .db import Base, SessionLocal, DB_PATH
import sqlite3
from ..services import accounts as account_service
import re
from urllib.parse import urlparse


class Proxy(Base):
    """Модель прокси"""
    __tablename__ = 'proxies'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="Полная строка прокси")
    scheme: Mapped[str] = mapped_column(String(10), default="http", comment="http/https/socks5")
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    login: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    password: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    last_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="OK/FAIL/TIMEOUT")
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_check: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def parse_proxy_line(line: str) -> Optional[Dict]:
    """
    Парсит строку прокси в любом формате:
    - ip:port
    - user:pass@ip:port
    - http://user:pass@ip:port
    - socks5://user:pass@ip:port
    """
    s = line.strip()
    if not s:
        return None
    
    # Добавляем схему если нет
    if "://" not in s:
        s = "http://" + s
    
    try:
        u = urlparse(s)
        if not (u.hostname and u.port):
            return None
        
        return {
            "raw": line.strip(),
            "scheme": (u.scheme or "http").lower(),
            "host": u.hostname,
            "port": u.port,
            "login": u.username or "",
            "password": u.password or "",
            "server": f"{(u.scheme or 'http').lower()}://{u.hostname}:{u.port}",
        }
    except Exception:
        return None


def add_proxy(proxy_line: str) -> Optional[Dict]:
    """Добавить прокси в хранилище"""
    parsed = parse_proxy_line(proxy_line)
    if not parsed:
        return None
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Проверяем есть ли уже
        cursor.execute("SELECT id FROM proxies WHERE raw = ?", (parsed["raw"],))
        if cursor.fetchone():
            return None  # Уже есть
        
        # Добавляем
        cursor.execute("""
            INSERT INTO proxies (raw, scheme, host, port, login, password, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            parsed["raw"],
            parsed["scheme"],
            parsed["host"],
            parsed["port"],
            parsed["login"],
            parsed["password"],
            datetime.utcnow(),
            datetime.utcnow()
        ))
        conn.commit()
        
        parsed['id'] = cursor.lastrowid
        return parsed
        
    finally:
        conn.close()


def get_all_proxies() -> List[Dict]:
    """Получить все прокси"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, raw, scheme, host, port, login, password,
                   last_status, latency_ms, last_error, last_check,
                   created_at, updated_at
            FROM proxies
            ORDER BY id
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'raw': row[1],
                'scheme': row[2],
                'host': row[3],
                'port': row[4],
                'login': row[5],
                'password': row[6],
                'last_status': row[7],
                'latency_ms': row[8],
                'last_error': row[9],
                'last_check': row[10],
                'created_at': row[11],
                'updated_at': row[12],
                'server': f"{row[2]}://{row[3]}:{row[4]}"
            })
        
        return results
        
    finally:
        conn.close()


def update_proxy_status(proxy_id: int, status: str, latency_ms: Optional[int], error: str = ""):
    """Обновить статус проверки прокси"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE proxies 
            SET last_status = ?, latency_ms = ?, last_error = ?, last_check = ?, updated_at = ?
            WHERE id = ?
        """, (status, latency_ms, error, datetime.utcnow(), datetime.utcnow(), proxy_id))
        conn.commit()
    finally:
        conn.close()


def sync_from_accounts() -> int:
    """Синхронизировать прокси из аккаунтов"""
    accounts = account_service.list_accounts()
    added = 0
    
    for acc in accounts:
        if acc.proxy and acc.name != "demo_account":
            proxy = add_proxy(acc.proxy)
            if proxy:
                added += 1
    
    return added


def clear_all():
    """Очистить все прокси"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM proxies")
        conn.commit()
    finally:
        conn.close()

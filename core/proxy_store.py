"""
ProxyStore - единое хранилище прокси для SemTool
Хранит все прокси в SQLite, синхронизируется с аккаунтами
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import List, Optional, Dict
from .db import Base, SessionLocal


class ProxyRecord(Base):
    """Запись о прокси"""
    __tablename__ = 'proxy_store'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="Исходная строка прокси")
    scheme: Mapped[str] = mapped_column(String(10), nullable=False, default='http', comment="http/https/socks5")
    host: Mapped[str] = mapped_column(String(100), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    login: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    password: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_status: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="OK/FAIL/TIMEOUT")
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Задержка в мс")
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_check: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


def parse_proxy_line(line: str) -> Optional[Dict]:
    """
    Парсит строку прокси в любом формате
    Поддержка: ip:port, ip:port@user:pass, http://user:pass@ip:port, socks5://...
    """
    from urllib.parse import urlparse
    
    s = line.strip()
    if not s:
        return None
    
    # Формат SemTool: ip:port@user:pass
    if '@' in s and not s.startswith(('http://', 'https://', 'socks')):
        parts = s.split('@', 1)
        if len(parts) == 2 and ':' in parts[0] and ':' in parts[1]:
            server_part = parts[0]  # ip:port
            auth_part = parts[1]     # user:pass
            host, port = server_part.split(':', 1)
            login, password = auth_part.split(':', 1)
            return {
                "raw": s,
                "scheme": "http",
                "host": host,
                "port": int(port),
                "login": login,
                "password": password,
                "server": f"http://{server_part}"
            }
    
    # Добавляем http:// если нет протокола
    if "://" not in s:
        s = "http://" + s
    
    try:
        parsed = urlparse(s)
        if not (parsed.hostname and parsed.port):
            return None
        
        return {
            "raw": line.strip(),
            "scheme": (parsed.scheme or "http").lower(),
            "host": parsed.hostname,
            "port": parsed.port,
            "login": parsed.username or "",
            "password": parsed.password or "",
            "server": f"{(parsed.scheme or 'http').lower()}://{parsed.hostname}:{parsed.port}"
        }
    except:
        return None


def add_proxy(raw: str) -> Optional[ProxyRecord]:
    """
    Добавляет прокси в хранилище
    Возвращает ProxyRecord или None если не удалось распарсить
    """
    parsed = parse_proxy_line(raw)
    if not parsed:
        return None
    
    session = SessionLocal()
    try:
        # Проверяем существует ли уже
        existing = session.query(ProxyRecord).filter_by(raw=parsed["raw"]).first()
        if existing:
            return existing
        
        # Создаем новую запись
        proxy = ProxyRecord(
            raw=parsed["raw"],
            scheme=parsed["scheme"],
            host=parsed["host"],
            port=parsed["port"],
            login=parsed["login"] or None,
            password=parsed["password"] or None
        )
        session.add(proxy)
        session.commit()
        session.refresh(proxy)
        return proxy
    finally:
        session.close()


def get_all_proxies() -> List[Dict]:
    """
    Возвращает все прокси из хранилища
    """
    session = SessionLocal()
    try:
        proxies = session.query(ProxyRecord).order_by(ProxyRecord.id.desc()).all()
        result = []
        for p in proxies:
            result.append({
                'id': p.id,
                'raw': p.raw,
                'scheme': p.scheme,
                'host': p.host,
                'port': p.port,
                'login': p.login or '',
                'password': p.password or '',
                'last_status': p.last_status,
                'latency_ms': p.latency_ms,
                'last_error': p.last_error,
                'last_check': p.last_check,
                'server': f"{p.scheme}://{p.host}:{p.port}"
            })
        return result
    finally:
        session.close()


def update_proxy_status(proxy_id: int, status: str, latency_ms: Optional[int] = None, error: Optional[str] = None):
    """
    Обновляет статус проверки прокси
    """
    session = SessionLocal()
    try:
        proxy = session.query(ProxyRecord).filter_by(id=proxy_id).first()
        if proxy:
            proxy.last_status = status
            proxy.latency_ms = latency_ms
            proxy.last_error = error
            proxy.last_check = datetime.utcnow()
            session.commit()
    finally:
        session.close()


def sync_from_accounts() -> int:
    """
    Синхронизирует прокси из аккаунтов в ProxyStore
    Возвращает количество добавленных прокси
    """
    from ..services import accounts as account_service
    
    accounts = account_service.list_accounts()
    added = 0
    
    for acc in accounts:
        if acc.proxy:
            proxy = add_proxy(acc.proxy)
            if proxy:
                added += 1
    
    return added


def clear_all():
    """Очищает все прокси из хранилища"""
    session = SessionLocal()
    try:
        session.query(ProxyRecord).delete()
        session.commit()
    finally:
        session.close()


def delete_proxy(proxy_id: int):
    """Удаляет прокси по ID"""
    session = SessionLocal()
    try:
        proxy = session.query(ProxyRecord).filter_by(id=proxy_id).first()
        if proxy:
            session.delete(proxy)
            session.commit()
    finally:
        session.close()

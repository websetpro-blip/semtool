from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select

from ..core.db import SessionLocal
from ..core.models import Account


def _auto_refresh(session):
    now = datetime.utcnow()
    stmt = select(Account).where(Account.status.in_(['cooldown', 'captcha']))
    for acc in session.execute(stmt).scalars():
        if acc.cooldown_until and acc.cooldown_until <= now:
            acc.status = 'ok'
            acc.cooldown_until = None
            acc.captcha_tries = 0
    session.commit()


def list_accounts() -> list[Account]:
    with SessionLocal() as session:
        _auto_refresh(session)
        result = session.execute(select(Account).order_by(Account.name))
        return list(result.scalars())


def create_account(name: str, profile_path: str, proxy: str | None = None, notes: str | None = None) -> Account:
    with SessionLocal() as session:
        account = Account(name=name, profile_path=profile_path, proxy=proxy or None, notes=notes)
        session.add(account)
        session.commit()
        session.refresh(account)
        return account


def upsert_account(name: str, profile_path: str, proxy: str | None = None, notes: str | None = None) -> Account:
    with SessionLocal() as session:
        stmt = select(Account).where(Account.name == name)
        existing = session.execute(stmt).scalar_one_or_none()
        if existing:
            existing.profile_path = profile_path
            existing.proxy = proxy or None
            existing.notes = notes
            session.commit()
            session.refresh(existing)
            return existing
        account = Account(name=name, profile_path=profile_path, proxy=proxy or None, notes=notes)
        session.add(account)
        session.commit()
        session.refresh(account)
        return account


def update_account(account_id: int, **fields) -> Account:
    with SessionLocal() as session:
        account = session.get(Account, account_id)
        if account is None:
            raise ValueError(f'Account {account_id} not found')
        for key, value in fields.items():
            if hasattr(account, key):
                setattr(account, key, value)
        session.commit()
        session.refresh(account)
        return account


def delete_account(account_id: int) -> None:
    with SessionLocal() as session:
        account = session.get(Account, account_id)
        if account:
            session.delete(account)
            session.commit()


def set_status(account_id: int, status: str, *, cooldown_minutes: int | None = None, captcha_increment: bool = False) -> Account:
    with SessionLocal() as session:
        account = session.get(Account, account_id)
        if account is None:
            raise ValueError(f'Account {account_id} not found')
        account.status = status
        if cooldown_minutes is not None:
            account.cooldown_until = datetime.utcnow() + timedelta(minutes=cooldown_minutes)
        elif status == 'ok':
            account.cooldown_until = None
        if captcha_increment:
            account.captcha_tries = (account.captcha_tries or 0) + 1
        session.commit()
        session.refresh(account)
        return account


def mark_captcha(account_id: int, minutes: int = 30) -> Account:
    return set_status(account_id, 'captcha', cooldown_minutes=minutes, captcha_increment=True)


def mark_cooldown(account_id: int, minutes: int = 10) -> Account:
    return set_status(account_id, 'cooldown', cooldown_minutes=minutes)


def mark_error(account_id: int) -> Account:
    return set_status(account_id, 'error')


def mark_ok(account_id: int) -> Account:
    return set_status(account_id, 'ok')


def update_account_proxy(account_name: str, proxy: str | None) -> Account:
    """Обновить прокси у аккаунта по имени"""
    with SessionLocal() as session:
        stmt = select(Account).where(Account.name == account_name)
        account = session.execute(stmt).scalar_one_or_none()
        if account is None:
            raise ValueError(f'Account {account_name} not found')
        account.proxy = proxy
        session.commit()
        session.refresh(account)
        return account


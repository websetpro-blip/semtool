from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import select, func

from ..core.db import SessionLocal
from ..core.models import FrequencyResult

QUEUE_STATUSES = ("queued", "running", "ok", "error")


def enqueue_masks(masks: Iterable[str], region: int) -> int:
    """Add masks into freq_results, resetting non-ok rows to queued."""
    inserted = 0
    normalized = []
    for raw in masks:
        mask = (raw or "").strip()
        if mask:
            normalized.append(mask)
    if not normalized:
        return 0
    with SessionLocal() as session:
        for mask in normalized:
            stmt = select(FrequencyResult).where(
                FrequencyResult.mask == mask,
                FrequencyResult.region == region,
            )
            existing = session.scalars(stmt).first()
            if existing:
                if existing.status != 'ok':
                    existing.status = 'queued'
                    existing.freq_total = 0
                    existing.freq_exact = 0
                    existing.error = None
                    existing.attempts = 0
                    existing.updated_at = datetime.utcnow()
            else:
                session.add(FrequencyResult(mask=mask, region=region))
                inserted += 1
        session.commit()
    return inserted


def list_results(status: str | None = None, limit: int = 500) -> list[dict]:
    with SessionLocal() as session:
        stmt = select(FrequencyResult).order_by(FrequencyResult.updated_at.desc())
        if status and status != 'all':
            stmt = stmt.where(FrequencyResult.status == status)
        if limit:
            stmt = stmt.limit(limit)
        rows = session.scalars(stmt).all()
        return [
            {
                'mask': row.mask,
                'region': row.region,
                'status': row.status,
                'freq_total': row.freq_total,
                'freq_exact': row.freq_exact,
                'attempts': row.attempts,
                'error': row.error or '',
                'updated_at': row.updated_at,
            }
            for row in rows
        ]


def counts_by_status() -> dict[str, int]:
    with SessionLocal() as session:
        stmt = select(FrequencyResult.status, func.count(FrequencyResult.id)).group_by(FrequencyResult.status)
        rows = session.execute(stmt).all()
        counts: dict[str, int] = {status: 0 for status in QUEUE_STATUSES}
        for status, value in rows:
            counts[status] = value
        return counts


def clear_results() -> None:
    with SessionLocal() as session:
        session.query(FrequencyResult).delete()
        session.commit()

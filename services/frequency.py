from __future__ import annotations
import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Iterable, Literal, Optional, Sequence

from sqlalchemy import select, func

from ..core.db import SessionLocal
from ..core.models import FrequencyResult

# Modes:
#   WS   -> broad wordstat frequency
#   "WS" -> quoted (exact phrase) frequency
#   !WS  -> exact with operators (using exclamation to fix word forms)
FrequencyMode = Literal["WS", '"WS"', "!WS"]

QUEUE_STATUSES = ("queued", "running", "ok", "error")


def enqueue_masks(masks: Iterable[str], region: int) -> int:
    """Add masks into freq_results, resetting non-ok rows to queued.

    Ensures id(mask, region) uniqueness, and re-queues rows that aren't ok yet.
    Returns number of affected/inserted rows.
    """
    inserted = 0
    normalized: list[str] = []
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
                if existing.status != "ok":
                    existing.status = "queued"
                    existing.freq_total = 0
                    existing.freq_quotes = 0
                    existing.freq_exact = 0
                    existing.error = None
                    existing.updated_at = datetime.utcnow()
                # if OK, leave as is
            else:
                fr = FrequencyResult(
                    mask=mask,
                    region=region,
                    status="queued",
                    freq_total=0,
                    freq_quotes=0,
                    freq_exact=0,
                    error=None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(fr)
                inserted += 1
        session.commit()
    return inserted


@dataclass
class ParseResult:
    total: int = 0      # WS broad
    quotes: int = 0     # "WS"
    exact: int = 0      # !WS


async def parse_frequency(mask: str, geo_id: Optional[int] = None) -> ParseResult:
    """Parse Yandex Wordstat frequencies for a single mask.

    This is a stub/mocked implementation with a clear structure for real parsing.
    - Integrate real HTTP client + CAPTCHA handling inside marked section.
    - geo_id is forwarded to request params when supported.
    """
    # --- MOCK/TEST IMPLEMENTATION START ---
    # Deterministic mock: based on simple hashing so tests stay stable
    base = abs(hash((mask.strip().lower(), geo_id))) % 10000
    total = base + 100
    quotes = int(total * 0.4)
    exact = int(total * 0.25)
    await asyncio.sleep(0)  # yield control to event loop
    return ParseResult(total=total, quotes=quotes, exact=exact)
    # --- MOCK/TEST IMPLEMENTATION END ---

    # --- REAL IMPLEMENTATION TEMPLATE (leave below for future devs) ---
    # async with http_client() as client:
    #     params = {"geo": geo_id} if geo_id is not None else {}
    #     total = await fetch_ws(client, mask, params=params)
    #     quotes = await fetch_ws(client, f'"{mask}"', params=params)
    #     exact = await fetch_ws(client, f'!{mask}', params=params)
    #     return ParseResult(total=total, quotes=quotes, exact=exact)


async def collect_for_masks(
    masks: Sequence[str],
    region: int,
    *,
    geo_id: Optional[int] = None,
    concurrency: int = 5,
) -> list[FrequencyResult]:
    """Collect frequencies for given masks and persist them to DB.

    - Updates statuses: queued -> running -> ok/error
    - Stores per-mode frequencies into FrequencyResult
    - Respects geo_id
    """
    sem = asyncio.Semaphore(concurrency)

    async def worker(mask: str) -> Optional[FrequencyResult]:
        async with sem:
            try:
                with SessionLocal() as session:
                    row = session.scalars(
                        select(FrequencyResult).where(
                            FrequencyResult.mask == mask,
                            FrequencyResult.region == region,
                        )
                    ).first()
                    if not row:
                        row = FrequencyResult(
                            mask=mask,
                            region=region,
                            status="queued",
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        session.add(row)
                        session.commit()
                        session.refresh(row)

                    row.status = "running"
                    row.updated_at = datetime.utcnow()
                    session.commit()

                # parse outside the session to avoid blocking
                parsed = await parse_frequency(mask, geo_id=geo_id)

                with SessionLocal() as session:
                    row = session.scalars(
                        select(FrequencyResult).where(
                            FrequencyResult.mask == mask,
                            FrequencyResult.region == region,
                        )
                    ).first()
                    if not row:
                        return None
                    row.freq_total = parsed.total
                    row.freq_quotes = parsed.quotes
                    row.freq_exact = parsed.exact
                    row.status = "ok"
                    row.error = None
                    row.updated_at = datetime.utcnow()
                    session.commit()
                    session.refresh(row)
                    return row
            except Exception as e:  # broad catch to store error on the row
                with SessionLocal() as session:
                    row = session.scalars(
                        select(FrequencyResult).where(
                            FrequencyResult.mask == mask,
                            FrequencyResult.region == region,
                        )
                    ).first()
                    if row:
                        row.status = "error"
                        row.error = str(e)
                        row.updated_at = datetime.utcnow()
                        session.commit()
                return None

    tasks = [worker(m) for m in masks]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


def export_results(region: int, *, only_ok: bool = True) -> list[dict]:
    """Export results for a region as list of dicts (for CSV/JSON).

    The dict schema:
      {
        "mask": str,
        "region": int,
        "freq_total": int,   # WS
        "freq_quotes": int,  # "WS"
        "freq_exact": int,   # !WS
        "status": str,
        "error": Optional[str],
        "updated_at": datetime,
      }
    """
    with SessionLocal() as session:
        stmt = select(FrequencyResult).where(FrequencyResult.region == region)
        if only_ok:
            stmt = stmt.where(FrequencyResult.status == "ok")
        stmt = stmt.order_by(func.lower(FrequencyResult.mask))
        rows = session.scalars(stmt).all()
        out: list[dict] = []
        for r in rows:
            out.append(
                {
                    "mask": r.mask,
                    "region": r.region,
                    "freq_total": int(r.freq_total or 0),
                    "freq_quotes": int(r.freq_quotes or 0),
                    "freq_exact": int(r.freq_exact or 0),
                    "status": r.status,
                    "error": r.error,
                    "updated_at": r.updated_at,
                }
            )
        return out


# Convenience function for synchronous contexts

def collect_sync(masks: Sequence[str], region: int, *, geo_id: Optional[int] = None, concurrency: int = 5) -> list[FrequencyResult]:
    return asyncio.run(collect_for_masks(masks, region, geo_id=geo_id, concurrency=concurrency))

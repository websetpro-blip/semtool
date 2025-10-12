from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

# from ...collector.parser import deep_run
def deep_run(*args, **kwargs):
    """Заглушка для deep_run"""
    pass

RESULTS_DIR = Path('results')
RESULTS_DIR.mkdir(exist_ok=True)

CONFIG_PATH = Path('collector') / 'accounts.yaml'


def run_deep_task(
    seeds_file: str,
    depth: int = 2,
    min_shows: int = 100,
    expand_min: int = 1000,
    topk: int = 50,
    region: Optional[int] = None,
    *,
    timestamp: str | None = None,
) -> Path:
    seeds_path = Path(seeds_file).expanduser().resolve()
    if not seeds_path.exists():
        raise FileNotFoundError(seeds_path)
    seeds = [line.strip() for line in seeds_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    if not seeds:
        raise ValueError('Seeds file is empty')

    stamp = timestamp or datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = RESULTS_DIR / f'deep_{stamp}.csv'

    deep_run(
        seeds=seeds,
        cfg_path=str(CONFIG_PATH.resolve()),
        depth=depth,
        min_shows=min_shows,
        expand_min=expand_min,
        topk=topk,
        lr=region,
        out_csv=str(out_path),
    )
    return out_path

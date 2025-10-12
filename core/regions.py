from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List
import json

DATA_FILE = Path(__file__).resolve().parent.parent / 'data' / 'regions.json'


@dataclass(frozen=True)
class Region:
    id: int
    name: str


_DEFAULT_REGIONS: tuple[Region, ...] = (
    Region(0, 'Все регионы'),
    Region(225, 'Россия'),
    Region(213, 'Москва'),
    Region(2, 'Санкт-Петербург'),
    Region(187, 'Екатеринбург'),
    Region(157, 'Новосибирск'),
    Region(197, 'Нижний Новгород'),
    Region(149, 'Казань'),
    Region(158, 'Самара'),
    Region(159, 'Омск'),
    Region(160, 'Ростов-на-Дону'),
    Region(162, 'Челябинск'),
    Region(163, 'Уфа'),
    Region(164, 'Волгоград'),
    Region(166, 'Красноярск'),
    Region(167, 'Пермь'),
    Region(168, 'Воронеж'),
    Region(169, 'Саратов'),
    Region(170, 'Краснодар'),
    Region(191, 'Иркутск'),
    Region(193, 'Хабаровск'),
    Region(221, 'Сочи'),
    Region(54, 'Ярославль'),
    Region(75, 'Тула'),
    Region(78, 'Тверь'),
    Region(113, 'Брянск'),
)


def _load_external_regions() -> List[Region]:
    if not DATA_FILE.exists():
        return []
    try:
        raw = json.loads(DATA_FILE.read_text(encoding='utf-8-sig'))
    except (OSError, json.JSONDecodeError):
        return []
    regions: list[Region] = []
    for item in raw:
        try:
            rid = int(item['id'])
            name = str(item['name']).strip()
        except (KeyError, TypeError, ValueError):
            continue
        if not name or '\ufffd' in name:
            continue
        regions.append(Region(rid, name))
    return regions


def load_regions() -> List[Region]:
    regions = _load_external_regions()
    if not regions:
        regions = list(_DEFAULT_REGIONS)
    return regions


def iter_region_names(regions: Iterable[Region]) -> Iterable[str]:
    for region in regions:
        yield region.name

# -*- coding: utf-8 -*-
"""
Helpers for fixing mojibake strings that were double-encoded.

Example of corruption this handles:
    "РќРµ РїРѕРЅСЏС‚РЅРѕ"  ->  "Не понятно"
"""

from __future__ import annotations

from typing import Optional


def fix_mojibake(value: Optional[str]) -> Optional[str]:
    """Attempt to recover typical cp1251/latin1 mojibake artifacts.

    The conversion is best-effort: if decoding fails we return the original
    string untouched to avoid swallowing information.
    """
    if value is None or not isinstance(value, str):
        return value

    # Heuristic: only attempt recovery if mojibake markers present
    suspicious = any(ch in value for ch in ("Ð", "Ñ", "Ò", "Ó", "Р", "Ѓ", "�"))
    if not suspicious:
        return value

    # Try latin1 -> utf-8 (common when UTF-8 bytes were read as latin1)
    try:
        return value.encode("latin1").decode("utf-8")
    except UnicodeError:
        pass

    # Try cp1251 -> utf-8 (second common variant)
    try:
        return value.encode("cp1251", errors="ignore").decode("utf-8", errors="ignore")
    except UnicodeError:
        return value

    return value


def fix_dict_strings(data: dict) -> dict:
    """Recursively fix all string values inside a dict."""
    from collections.abc import Mapping, MutableMapping

    if isinstance(data, MutableMapping):
        for key, val in list(data.items()):
            if isinstance(val, str):
                data[key] = fix_mojibake(val)
            elif isinstance(val, Mapping):
                data[key] = fix_dict_strings(dict(val))
            elif isinstance(val, list):
                data[key] = [fix_mojibake(item) if isinstance(item, str) else item for item in val]
    return data

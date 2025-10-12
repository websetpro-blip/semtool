from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - surface informative error later
    yaml = None  # type: ignore


class ConfigError(RuntimeError):
    """Raised when configuration cannot be loaded."""


CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
RUNNER_FILE = CONFIG_DIR / "runner.yaml"
DEFAULT_PROFILES_ROOT = Path(".profiles")


def _ensure_yaml_loader():
    if yaml is None:
        raise ConfigError(
            "PyYAML is required to parse runner.yaml. Install it with 'pip install pyyaml'."
        )
    return yaml


@dataclass
class RunnerAccount:
    profile: str
    proxy: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class RunnerConfig:
    headless: bool = False
    manual_login: bool = False
    autocaptcha: bool = False
    keep_context: bool = True
    max_concurrent_pages: int = 1
    cooldown_sec: dict[str, int] = field(default_factory=dict)
    retry_policy: dict[str, int] = field(default_factory=dict)
    region: dict[str, Any] = field(default_factory=dict)
    pool: list[RunnerAccount] = field(default_factory=list)


def load_runner_config(path: str | Path | None = None) -> RunnerConfig:
    """Load runner.yaml (or alternative path) into a structured object."""
    target = Path(path) if path else RUNNER_FILE
    if not target.exists():
        raise ConfigError(f"runner.yaml not found at {target}")

    loader = _ensure_yaml_loader()
    try:
        raw_data: Any = loader.safe_load(target.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - surface config/parse errors plainly
        raise ConfigError(f"Failed to parse runner config: {exc}") from exc

    data: dict[str, Any] = raw_data or {}

    pool_entries: list[RunnerAccount] = []
    raw_pool = data.get("pool")
    if isinstance(raw_pool, list):
        for entry in raw_pool:
            if not isinstance(entry, dict):
                continue
            profile = str(entry.get("profile") or "").strip()
            if not profile:
                continue
            proxy_value = entry.get("proxy")
            proxy = str(proxy_value).strip() if proxy_value is not None else None
            status_value = entry.get("status")
            status = str(status_value).strip() if status_value is not None else None
            notes_value = entry.get("notes")
            notes = str(notes_value).strip() if notes_value is not None else None
            pool_entries.append(
                RunnerAccount(
                    profile=profile,
                    proxy=proxy or None,
                    status=status or None,
                    notes=notes or None,
                )
            )

    return RunnerConfig(
        headless=bool(data.get("headless", False)),
        manual_login=bool(data.get("manual_login", False)),
        autocaptcha=bool(data.get("autocaptcha", False)),
        keep_context=bool(data.get("keep_context", True)),
        max_concurrent_pages=int(data.get("max_concurrent_pages", 1) or 1),
        cooldown_sec=data.get("cooldown_sec") or {},
        retry_policy=data.get("retry_policy") or {},
        region=data.get("region") or {},
        pool=pool_entries,
    )


def resolve_default_lr(config: RunnerConfig, fallback: int = 213) -> int:
    """Return lr code from config.region (falls back to 213)."""
    lr_value = None
    if isinstance(config.region, dict):
        lr_value = config.region.get("lr")
    if lr_value is None:
        return fallback
    try:
        return int(lr_value)
    except (TypeError, ValueError):
        return fallback


def sync_accounts_with_runner(config: RunnerConfig, profiles_root: str | Path | None = None) -> None:
    """Ensure accounts from runner config exist in the SQLite pool."""
    from .db import SessionLocal, ensure_schema
    from .models import Account

    ensure_schema()
    root = Path(profiles_root) if profiles_root else DEFAULT_PROFILES_ROOT

    with SessionLocal() as session:
        existing = {acc.name: acc for acc in session.query(Account).all()}
        for entry in config.pool:
            profile_path = str((root / entry.profile).resolve()) if root.is_absolute() else str(root / entry.profile)
            account = existing.get(entry.profile)
            if account is None:
                account = Account(name=entry.profile, profile_path=profile_path)
                session.add(account)
            else:
                account.profile_path = profile_path
            if entry.proxy is not None:
                account.proxy = entry.proxy
            if entry.status:
                account.status = entry.status
            if entry.notes:
                account.notes = entry.notes
        session.commit()


__all__ = [
    "ConfigError",
    "RunnerAccount",
    "RunnerConfig",
    "DEFAULT_PROFILES_ROOT",
    "load_runner_config",
    "resolve_default_lr",
    "sync_accounts_with_runner",
]
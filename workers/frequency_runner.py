from __future__ import annotations

from datetime import datetime
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
import traceback

from ..core.settings import ConfigError, load_runner_config, sync_accounts_with_runner

from ..core.db import SessionLocal
from ..core.models import Account, Task
from ..services import accounts as account_service
from ..services import tasks as task_service

# from ...collector.selenium_worker import run as run_frequency

RESULTS_DIR = Path('results')
RESULTS_DIR.mkdir(exist_ok=True)
LOGS_DIR = Path('results') / 'gui_logs'
LOGS_DIR.mkdir(parents=True, exist_ok=True)


_CONFIG_SYNCED = False


def _append_log(path: Path, message: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(message.rstrip() + "\n")
    except OSError:
        pass


def _ensure_runner_accounts_synced() -> None:
    global _CONFIG_SYNCED
    if _CONFIG_SYNCED:
        return
    try:
        config = load_runner_config()
    except ConfigError as exc:
        print(f"[runner-config] {exc}")
        _CONFIG_SYNCED = True
        return
    sync_accounts_with_runner(config)
    _CONFIG_SYNCED = True


CAPTCHA_KEYWORDS = ('captcha', 'showcaptcha')
RELOGIN_KEYWORDS = ('relogin', 'passport')


def execute_task(task_id: int) -> None:
    _ensure_runner_accounts_synced()

    with SessionLocal() as session:
        task = session.get(Task, task_id)
        if task is None:
            raise ValueError(f'Task {task_id} not found')
        if task.kind != 'frequency':
            raise ValueError(f'Task {task_id} has unexpected kind {task.kind}')
        if task.account_id is None:
            raise ValueError(f'Task {task_id} is missing account reference')
        account = session.get(Account, task.account_id)
        if account is None:
            raise ValueError(f'Account {task.account_id} not found')

    seeds_path = Path(task.seed_file).expanduser().resolve()
    if not seeds_path.exists():
        task_service.update_task_status(task.id, 'failed', error_message=f'Seed file {seeds_path} not found')
        return

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = RESULTS_DIR / f"freq_{account.name}_{timestamp}.csv"
    log_path = LOGS_DIR / f"freq_{account.name}_{timestamp}.log"

    task_service.update_task_status(task.id, 'running', started_at=datetime.utcnow(), log_path=str(log_path))
    account_service.mark_ok(account.id)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with log_path.open("w", encoding="utf-8") as log_handle:
            log_handle.write(f"[{timestamp}] start task #{task.id} -> {seeds_path}\n")
            log_handle.flush()
            # with redirect_stdout(log_handle), redirect_stderr(log_handle):
            #     run_frequency(
            #         profile=account.name,
            #         proxy=account.proxy,
            #         seeds=seeds_path,
            #         out=out_path,
            #         lr=task.region,
            #         headless=bool(task.headless),
            #         dump_json=bool(task.dump_json),
            #         manual_login=not bool(task.headless),
            #     )
            pass  # Временно отключено
            log_handle.write(f"[{timestamp}] completed -> {out_path}\n")
        task_service.update_task_status(task.id, 'completed', finished_at=datetime.utcnow(), output_path=str(out_path))
        account_service.mark_ok(account.id)
    except SystemExit as exc:
        message = str(exc)
        _append_log(log_path, f"SystemExit: {message}")
        task_service.update_task_status(task.id, 'failed', finished_at=datetime.utcnow(), error_message=message)
        account_service.set_status(account.id, 'disabled')
        raise
    except Exception as exc:
        message = str(exc)
        _append_log(log_path, f"Exception: {message}")
        _append_log(log_path, traceback.format_exc())
        task_service.update_task_status(task.id, 'failed', finished_at=datetime.utcnow(), error_message=message)
        lowered = message.lower()
        if any(keyword in lowered for keyword in CAPTCHA_KEYWORDS):
            account_service.mark_captcha(account.id)
        elif any(keyword in lowered for keyword in RELOGIN_KEYWORDS):
            account_service.set_status(account.id, 'disabled')
        else:
            account_service.mark_error(account.id)
        raise


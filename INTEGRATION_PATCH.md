# Патч для интеграции сессий в keyset

## Что добавлено:

### 1. Новые модули:
- `keyset/services/sessions.py` - управление сессиями
- `keyset/workers/session_frequency_runner.py` - парсер с сессиями
- `keyset/app/sessions_tab.py` - UI вкладка

### 2. Изменения в main.py:

#### Добавить импорт в начало файла:
```python
from .sessions_tab import SessionsTab, SessionFrequencyThread
```

#### В класс CollectTab добавить:

**После `self.dump_json_check`:**
```python
# Режим парсинга
self.mode_combo = QComboBox()
self.mode_combo.addItem("Старый режим (запуск браузера)", "old")
self.mode_combo.addItem("Через сессии (рекомендуется)", "sessions")
self.mode_combo.setCurrentIndex(1)  # По умолчанию - сессии
```

**В form.addRow после dump_json_check:**
```python
form.addRow("Режим парсинга:", self.mode_combo)
```

**В метод `start_task` в начале после проверки аккаунтов:**
```python
mode = self.mode_combo.currentData()

if mode == "sessions":
    # Новый режим через сессии
    self.start_session_task()
    return
```

**Добавить новый метод в CollectTab:**
```python
def start_session_task(self) -> None:
    """Запуск через сохранённые сессии"""
    accounts = account_service.list_accounts()
    active_accounts = [acc for acc in accounts if acc.status == 'ok']
    if not active_accounts:
        QMessageBox.warning(self, "Аккаунты", "Нет активных аккаунтов со статусом 'ok'.")
        return

    manual_lines = [line.strip() for line in self.seed_text.toPlainText().splitlines() if line.strip()]
    seed_file = self.seed_edit.text().strip() or None
    if not manual_lines and not seed_file:
        QMessageBox.warning(self, "Нет данных", "Добавьте фразы вручную или выберите файл с масками.")
        return
    
    try:
        seeds_path = materialize_seeds(manual_lines, seed_file, "freq_manual")
    except (FileNotFoundError, ValueError) as exc:
        QMessageBox.warning(self, "Ошибка", str(exc))
        return

    # Читаем маски из файла
    masks = [line.strip() for line in seeds_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    
    combo_data = self.region_combo.currentData()
    region = int(combo_data) if combo_data is not None else 225
    headless = self.headless_check.isChecked()
    
    # Используем первый доступный аккаунт
    account_id = active_accounts[0].id
    
    self._log(f"Запуск сбора через сессию (аккаунт #{account_id}): {len(masks)} масок, регион {region}")
    self.start_btn.setEnabled(False)
    
    # Создаём воркер
    self._worker = SessionFrequencyThread(
        account_id=account_id,
        masks=masks,
        region=region,
        headless=headless
    )
    self._worker.log_message.connect(self._log)
    self._worker.finished.connect(self._session_task_finished)
    self._worker.start()

def _session_task_finished(self, success: bool, message: str) -> None:
    self.start_btn.setEnabled(True)
    self._worker = None
    self._log(message)
    if success:
        QMessageBox.information(self, "Частотность", "Сбор завершён успешно.")
    else:
        QMessageBox.warning(self, "Частотность", message)
    if self.tasks_tab:
        self.tasks_tab.refresh()
    if self.results_tab:
        self.results_tab.refresh()
```

**Добавить SessionFrequencyThread перед классом AccountsTab:**
```python
class SessionFrequencyThread(QThread):
    """Поток для парсинга через сессии"""
    
    log_message = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, account_id: int, masks: list[str], region: int, headless: bool) -> None:
        super().__init__()
        self.account_id = account_id
        self.masks = masks
        self.region = region
        self.headless = headless
    
    def run(self) -> None:
        from ..workers.session_frequency_runner import parse_frequency_with_session
        
        def progress_callback(mask, freq, idx, total):
            self.log_message.emit(f"[{idx}/{total}] {mask}: {freq:,}")
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            stats = loop.run_until_complete(
                parse_frequency_with_session(
                    self.account_id,
                    self.masks,
                    self.region,
                    self.headless,
                    on_progress=progress_callback
                )
            )
            
            loop.close()
            
            message = f"Готово! Успешно: {stats['success']}, Ошибок: {stats['failed']}"
            self.finished.emit(True, message)
        
        except Exception as exc:
            self.finished.emit(False, str(exc))
```

#### В класс MainWindow добавить:

**После создания всех вкладок:**
```python
self.sessions_tab = SessionsTab(self.log_widget)
```

**В tabs.addTab (добавить после accounts_tab):**
```python
tabs.addTab(self.sessions_tab, "Сессии")
```

**После всех addTab:**
```python
# Связываем изменения сессий с обновлением других вкладок
self.sessions_tab.sessions_changed.connect(self.accounts_tab.refresh)
```

## Как использовать:

1. **Перейдите на вкладку "Сессии"**
2. **Выберите аккаунт и нажмите "Создать сессию"**
3. **Залогиньтесь в открывшемся браузере (3 минуты)**
4. **Готово! Теперь на вкладке "Сбор частотности":**
   - Выберите режим "Через сессии"
   - Вставьте маски
   - Запустите сбор
   - Всё работает БЕЗ повторного логина!

## Преимущества:

✅ Логин ОДИН РАЗ  
✅ Результаты сразу в БД  
✅ Видно прогресс в реальном времени  
✅ Можно headless режим для массового парсинга  
✅ Не надо скачивать CSV - всё в таблице "Результаты частотности"  

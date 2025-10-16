"""
Миграция: Создание таблицы proxies
Запустить: python scripts/migrate_proxies_table.py
"""

import sqlite3
from pathlib import Path


def migrate():
    """Создать таблицу proxies"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    db_path = project_root / "data" / "keyset.db"
    
    if not db_path.exists():
        print(f"[ERROR] База данных не найдена: {db_path}")
        db_path = Path("C:/AI/yandex/keyset/data/keyset.db")
        if not db_path.exists():
            print(f"[ERROR] БД не найдена и там: {db_path}")
            return False
    
    print(f"[INFO] Подключаюсь к {db_path}...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем есть ли таблица
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='proxies'")
        if cursor.fetchone():
            print("[INFO] Таблица proxies уже существует")
            return True
        
        # Создаем таблицу
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proxies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw VARCHAR(255) NOT NULL UNIQUE,
                scheme VARCHAR(10) DEFAULT 'http',
                host VARCHAR(255) NOT NULL,
                port INTEGER NOT NULL,
                login VARCHAR(100),
                password VARCHAR(100),
                last_status VARCHAR(20),
                latency_ms INTEGER,
                last_error TEXT,
                last_check TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        print("[OK] Таблица proxies создана")
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка миграции: {e}")
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()

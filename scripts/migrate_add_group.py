"""
Миграция: Добавление поля group в таблицу freq_results
Для группировки ключевых фраз (как в Key Collector)
Запустить: python scripts/migrate_add_group.py
"""

import sqlite3
from pathlib import Path


def migrate():
    """Добавить поле group в freq_results"""
    # Ищем БД относительно корня проекта
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    db_path = project_root / "data" / "keyset.db"
    
    if not db_path.exists():
        print(f"[ERROR] База данных не найдена: {db_path}")
        print(f"[INFO] Попытка поиска в текущей директории...")
        db_path = Path("C:/AI/yandex/keyset/data/keyset.db")
        if not db_path.exists():
            print(f"[ERROR] БД не найдена и там: {db_path}")
            return False
    
    print(f"[INFO] Подключаюсь к {db_path}...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем есть ли уже колонка
        cursor.execute("PRAGMA table_info(freq_results)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'group' in columns:
            print("[INFO] Колонка group уже существует")
            return True
        
        # Добавляем колонку
        print("[INFO] Добавляю колонку group...")
        cursor.execute("ALTER TABLE freq_results ADD COLUMN `group` VARCHAR(100)")
        conn.commit()
        
        print("[OK] Колонка group успешно добавлена!")
        print("[INFO] Теперь можно группировать ключи как в Key Collector")
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка миграции: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    print("="*60)
    print("Миграция: Добавление group в freq_results")
    print("="*60)
    
    if migrate():
        print("\n[SUCCESS] Миграция завершена успешно!")
    else:
        print("\n[FAIL] Миграция не удалась!")

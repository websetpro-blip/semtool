"""
Миграция: Добавление поля captcha_key в таблицу accounts
Запустить: python scripts/migrate_add_captcha_key.py
"""

import sqlite3
from pathlib import Path


def migrate():
    """Добавить поле captcha_key в accounts"""
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
        cursor.execute("PRAGMA table_info(accounts)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'captcha_key' in columns:
            print("[INFO] Колонка captcha_key уже существует")
            return True
        
        # Добавляем колонку
        print("[INFO] Добавляю колонку captcha_key...")
        cursor.execute("ALTER TABLE accounts ADD COLUMN captcha_key VARCHAR(100)")
        conn.commit()
        
        print("[OK] Колонка captcha_key успешно добавлена!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Ошибка миграции: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    print("="*60)
    print("Миграция: Добавление captcha_key в accounts")
    print("="*60)
    
    if migrate():
        print("\n[SUCCESS] Миграция завершена успешно!")
    else:
        print("\n[FAIL] Миграция не удалась!")

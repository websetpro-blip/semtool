# -*- coding: utf-8 -*-
from core.db import engine, ensure_schema, get_db_connection

# Update schema
ensure_schema()
print("[OK] DB schema updated successfully")

# Check tables
with get_db_connection() as conn:
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\nTables in database: {len(tables)}")
    for table in tables:
        print(f"  - {table}")
    
    # Check WAL mode
    cursor = conn.execute("PRAGMA journal_mode")
    mode = cursor.fetchone()[0]
    print(f"\nJournal mode: {mode}")
    
    # Check new tables specifically
    new_tables = ['frequencies', 'forecasts', 'clusters']
    print(f"\nNew turbo parser tables:")
    for table in new_tables:
        if table in tables:
            cursor = conn.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"  - {table}: {', '.join(columns)}")

print("\n[OK] Database ready for turbo parser pipeline!")

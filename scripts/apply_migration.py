#!/usr/bin/env python3
"""
Скрипт для применения миграции 002_add_mr_classification.sql
"""
import os
import sys
from pathlib import Path

# Добавляем путь к api модулю
if os.path.exists('/app'):
    sys.path.insert(0, '/app')
else:
    sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from mr_database import init_connection_pool, get_db_connection

def apply_migration():
    """Применить миграцию 002_add_mr_classification.sql"""
    init_connection_pool()
    
    migration_file = os.path.join(os.path.dirname(__file__), '..', 'api', 'migrations', '002_add_mr_classification.sql')
    
    if not os.path.exists(migration_file):
        print(f"❌ Файл миграции не найден: {migration_file}")
        return False
    
    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(migration_sql)
        
        print("✅ Миграция применена успешно")
        return True
    except Exception as e:
        error_str = str(e).lower()
        if "already exists" in error_str or "duplicate" in error_str:
            print("ℹ️  Миграция уже применена (колонки уже существуют)")
            return True
        else:
            print(f"❌ Ошибка применения миграции: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    apply_migration()





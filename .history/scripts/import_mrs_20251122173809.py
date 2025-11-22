#!/usr/bin/env python3
"""
Скрипт для импорта собранных MR в PostgreSQL базу данных
"""
import os
import sys
import json
import logging
from pathlib import Path

# Добавляем путь к api модулю
# Проверяем, запущены ли мы в Docker (где /app) или на хосте
if os.path.exists('/app'):
    # В Docker контейнере
    sys.path.insert(0, '/app')
else:
    # На хосте
    sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from mr_database import create_merge_request, init_connection_pool, init_mr_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def import_mrs_from_json(json_file: str, dry_run: bool = False):
    """
    Импортировать MR из JSON файла в БД
    
    Args:
        json_file: Путь к JSON файлу с MR
        dry_run: Если True, только проверяет данные без импорта
    """
    json_path = Path(json_file)
    
    if not json_path.exists():
        logger.error(f"JSON file not found: {json_file}")
        return
    
    # Инициализируем БД
    init_connection_pool()
    if not dry_run:
        init_mr_database()
    
    # Загружаем MR из JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        mrs = json.load(f)
    
    logger.info(f"Loaded {len(mrs)} MRs from {json_file}")
    
    imported = 0
    skipped = 0
    errors = 0
    
    for i, mr_data in enumerate(mrs, 1):
        try:
            if dry_run:
                logger.info(f"[DRY RUN] Would import MR {i}/{len(mrs)}: {mr_data.get('title', 'Unknown')[:50]}")
                imported += 1
            else:
                mr_id = create_merge_request(mr_data)
                if mr_id:
                    logger.info(f"Imported MR {i}/{len(mrs)}: ID={mr_id}, {mr_data.get('title', 'Unknown')[:50]}")
                    imported += 1
                else:
                    logger.warning(f"Failed to import MR {i}/{len(mrs)}: {mr_data.get('title', 'Unknown')[:50]}")
                    errors += 1
        except Exception as e:
            logger.error(f"Error importing MR {i}: {e}", exc_info=True)
            errors += 1
    
    logger.info(f"Import complete: {imported} imported, {skipped} skipped, {errors} errors")


def main():
    """Основная функция импорта"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import Merge Requests into PostgreSQL database')
    parser.add_argument('json_file', help='JSON file with MRs to import')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no actual import)')
    
    args = parser.parse_args()
    
    import_mrs_from_json(args.json_file, dry_run=args.dry_run)


if __name__ == '__main__':
    main()



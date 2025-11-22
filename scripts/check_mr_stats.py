#!/usr/bin/env python3
"""
Скрипт для проверки статистики MR в базе данных
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
from psycopg2.extras import RealDictCursor

def get_mr_statistics():
    """Получить статистику по MR"""
    init_connection_pool()
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Общее количество
                cur.execute("SELECT COUNT(*) as total FROM merge_requests")
                total = cur.fetchone()['total']
                
                # По типам
                cur.execute("""
                    SELECT 
                        mr_type,
                        COUNT(*) as count,
                        AVG(complexity_points) as avg_points,
                        MIN(complexity_points) as min_points,
                        MAX(complexity_points) as max_points
                    FROM merge_requests
                    GROUP BY mr_type
                    ORDER BY count DESC
                """)
                by_type = cur.fetchall()
                
                # По баллам сложности
                cur.execute("""
                    SELECT 
                        complexity_points,
                        COUNT(*) as count
                    FROM merge_requests
                    GROUP BY complexity_points
                    ORDER BY complexity_points
                """)
                by_points = cur.fetchall()
                
                # По языкам
                cur.execute("""
                    SELECT 
                        language,
                        COUNT(*) as count
                    FROM merge_requests
                    WHERE language IS NOT NULL
                    GROUP BY language
                    ORDER BY count DESC
                """)
                by_language = cur.fetchall()
                
                # По тегам стека
                cur.execute("""
                    SELECT 
                        unnest(stack_tags) as tag,
                        COUNT(*) as count
                    FROM merge_requests
                    WHERE stack_tags IS NOT NULL AND array_length(stack_tags, 1) > 0
                    GROUP BY tag
                    ORDER BY count DESC
                """)
                by_stack = cur.fetchall()
                
                # Источники
                cur.execute("""
                    SELECT 
                        metadata->>'source' as source,
                        COUNT(*) as count
                    FROM merge_requests
                    WHERE metadata IS NOT NULL AND metadata->>'source' IS NOT NULL
                    GROUP BY source
                    ORDER BY count DESC
                """)
                by_source = cur.fetchall()
                
                return {
                    'total': total,
                    'by_type': [dict(row) for row in by_type],
                    'by_points': [dict(row) for row in by_points],
                    'by_language': [dict(row) for row in by_language],
                    'by_stack': [dict(row) for row in by_stack],
                    'by_source': [dict(row) for row in by_source]
                }
    except Exception as e:
        print(f"Ошибка получения статистики: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None

def main():
    stats = get_mr_statistics()
    
    if not stats:
        print("❌ Не удалось получить статистику")
        print("💡 Возможно, база данных пуста или не подключена")
        return
    
    print("=" * 60)
    print("📊 СТАТИСТИКА MERGE REQUESTS")
    print("=" * 60)
    print(f"\n📦 Всего MR в базе: {stats['total']}")
    
    if stats['total'] == 0:
        print("\n⚠️  База данных пуста!")
        print("💡 Выполните сбор MR:")
        print("   docker compose exec api python scripts/collect_mrs.py --artifacts /artifacts --output /tmp/mrs_collected.json")
        print("   docker compose exec api python scripts/import_mrs.py /tmp/mrs_collected.json")
        return
    
    print("\n" + "=" * 60)
    print("📋 ПО ТИПАМ:")
    print("=" * 60)
    if stats['by_type']:
        for row in stats['by_type']:
            mr_type = row['mr_type'] or 'не указан'
            count = row['count']
            avg = row['avg_points'] or 0
            min_p = row['min_points'] or 0
            max_p = row['max_points'] or 0
            print(f"  {mr_type:20s} {count:3d} шт. | Баллы: {min_p:.0f}-{max_p:.0f} (среднее: {avg:.1f})")
    else:
        print("  Нет данных")
    
    print("\n" + "=" * 60)
    print("🎯 ПО БАЛЛАМ СЛОЖНОСТИ:")
    print("=" * 60)
    if stats['by_points']:
        for row in stats['by_points']:
            points = row['complexity_points']
            count = row['count']
            print(f"  {points} балл(ов): {count:3d} MR")
    else:
        print("  Нет данных")
    
    print("\n" + "=" * 60)
    print("🌐 ПО ЯЗЫКАМ:")
    print("=" * 60)
    if stats['by_language']:
        for row in stats['by_language']:
            lang = row['language'] or 'не указан'
            count = row['count']
            print(f"  {lang:15s} {count:3d} MR")
    else:
        print("  Нет данных")
    
    print("\n" + "=" * 60)
    print("🏷️  ПО ТЕГАМ СТЕКА:")
    print("=" * 60)
    if stats['by_stack']:
        for row in stats['by_stack']:
            tag = row['tag']
            count = row['count']
            print(f"  {tag:15s} {count:3d} MR")
    else:
        print("  Нет данных")
    
    print("\n" + "=" * 60)
    print("📂 ПО ИСТОЧНИКАМ:")
    print("=" * 60)
    if stats['by_source']:
        for row in stats['by_source']:
            source = row['source'] or 'не указан'
            count = row['count']
            print(f"  {source:20s} {count:3d} MR")
    else:
        print("  Нет данных")
    
    print("\n" + "=" * 60)
    print("✅ Статистика получена")
    print("=" * 60)

if __name__ == '__main__':
    main()





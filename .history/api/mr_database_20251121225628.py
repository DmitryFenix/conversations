# api/mr_database.py
"""
Модуль для работы с базой данных Merge Requests (PostgreSQL)
"""
import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.pool import SimpleConnectionPool
from typing import Optional, Dict, List, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Конфигурация PostgreSQL
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "mr_database")
POSTGRES_USER = os.getenv("POSTGRES_USER", "mr_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mr_password")

# Connection pool
_connection_pool = None


def init_connection_pool():
    """Инициализация пула соединений с PostgreSQL"""
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD
            )
            logger.info(f"PostgreSQL connection pool initialized: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection pool: {e}")
            _connection_pool = None
    return _connection_pool


@contextmanager
def get_db_connection():
    """Контекстный менеджер для получения соединения с БД"""
    pool = init_connection_pool()
    if pool is None:
        raise Exception("PostgreSQL connection pool not initialized")
    
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        pool.putconn(conn)


def init_mr_database():
    """Инициализация структуры БД (создание таблиц)"""
    migration_file = os.path.join(os.path.dirname(__file__), "migrations", "001_create_mr_tables.sql")
    
    if not os.path.exists(migration_file):
        logger.warning(f"Migration file not found: {migration_file}")
        return False
    
    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(migration_sql)
        
        logger.info("MR database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize MR database: {e}", exc_info=True)
        return False


def create_merge_request(mr_data: Dict[str, Any]) -> Optional[int]:
    """
    Создать новый Merge Request в БД
    
    Args:
        mr_data: Словарь с данными MR
        
    Returns:
        ID созданного MR или None при ошибке
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO merge_requests (
                        external_id, title, description, url,
                        author, created_at, merged_at, state,
                        language, languages, change_type,
                        files_changed, lines_added, lines_deleted, diff_size, complexity_score,
                        diff_content, diff_path,
                        has_tests, test_coverage, code_quality_score,
                        bugs_count, issues_detected, security_issues, performance_issues,
                        difficulty_level, review_time_estimate,
                        metadata, tags
                    ) VALUES (
                        %(external_id)s, %(title)s, %(description)s, %(url)s,
                        %(author)s, %(created_at)s, %(merged_at)s, %(state)s,
                        %(language)s, %(languages)s, %(change_type)s,
                        %(files_changed)s, %(lines_added)s, %(lines_deleted)s, %(diff_size)s, %(complexity_score)s,
                        %(diff_content)s, %(diff_path)s,
                        %(has_tests)s, %(test_coverage)s, %(code_quality_score)s,
                        %(bugs_count)s, %(issues_detected)s, %(security_issues)s, %(performance_issues)s,
                        %(difficulty_level)s, %(review_time_estimate)s,
                        %(metadata)s, %(tags)s
                    ) RETURNING id
                """, {
                    'external_id': mr_data.get('external_id'),
                    'title': mr_data.get('title', ''),
                    'description': mr_data.get('description'),
                    'url': mr_data.get('url'),
                    'author': mr_data.get('author'),
                    'created_at': mr_data.get('created_at'),
                    'merged_at': mr_data.get('merged_at'),
                    'state': mr_data.get('state', 'open'),
                    'language': mr_data.get('language'),
                    'languages': mr_data.get('languages', []),
                    'change_type': mr_data.get('change_type'),
                    'files_changed': mr_data.get('files_changed', 0),
                    'lines_added': mr_data.get('lines_added', 0),
                    'lines_deleted': mr_data.get('lines_deleted', 0),
                    'diff_size': mr_data.get('diff_size', 0),
                    'complexity_score': mr_data.get('complexity_score', 0),
                    'diff_content': mr_data.get('diff_content'),
                    'diff_path': mr_data.get('diff_path'),
                    'has_tests': mr_data.get('has_tests', False),
                    'test_coverage': mr_data.get('test_coverage'),
                    'code_quality_score': mr_data.get('code_quality_score'),
                    'bugs_count': mr_data.get('bugs_count', 0),
                    'issues_detected': mr_data.get('issues_detected', []),
                    'security_issues': mr_data.get('security_issues', 0),
                    'performance_issues': mr_data.get('performance_issues', 0),
                    'difficulty_level': mr_data.get('difficulty_level'),
                    'review_time_estimate': mr_data.get('review_time_estimate'),
                    'metadata': Json(mr_data.get('metadata', {})) if mr_data.get('metadata') else None,
                    'tags': mr_data.get('tags', [])
                })
                mr_id = cur.fetchone()[0]
                return mr_id
    except Exception as e:
        logger.error(f"Failed to create merge request: {e}", exc_info=True)
        return None


def get_merge_request(mr_id: int) -> Optional[Dict[str, Any]]:
    """Получить MR по ID"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM merge_requests WHERE id = %s", (mr_id,))
                row = cur.fetchone()
                if row:
                    return dict(row)
                return None
    except Exception as e:
        logger.error(f"Failed to get merge request {mr_id}: {e}", exc_info=True)
        return None


def list_merge_requests(
    language: Optional[str] = None,
    difficulty_level: Optional[str] = None,
    change_type: Optional[str] = None,
    min_complexity: Optional[float] = None,
    max_complexity: Optional[float] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Получить список MR с фильтрацией
    
    Args:
        language: Фильтр по языку
        difficulty_level: Фильтр по уровню сложности
        change_type: Фильтр по типу изменений
        min_complexity: Минимальная сложность
        max_complexity: Максимальная сложность
        limit: Лимит результатов
        offset: Смещение для пагинации
        
    Returns:
        Список MR
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM merge_requests WHERE 1=1"
                params = []
                
                if language:
                    query += " AND language = %s"
                    params.append(language)
                
                if difficulty_level:
                    query += " AND difficulty_level = %s"
                    params.append(difficulty_level)
                
                if change_type:
                    query += " AND change_type = %s"
                    params.append(change_type)
                
                if min_complexity is not None:
                    query += " AND complexity_score >= %s"
                    params.append(min_complexity)
                
                if max_complexity is not None:
                    query += " AND complexity_score <= %s"
                    params.append(max_complexity)
                
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cur.execute(query, params)
                rows = cur.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to list merge requests: {e}", exc_info=True)
        return []


def search_merge_requests(search_query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Полнотекстовый поиск по MR"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM merge_requests
                    WHERE to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, '')) 
                          @@ plainto_tsquery('english', %s)
                    ORDER BY ts_rank(
                        to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, '')),
                        plainto_tsquery('english', %s)
                    ) DESC
                    LIMIT %s
                """, (search_query, search_query, limit))
                rows = cur.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to search merge requests: {e}", exc_info=True)
        return []


def get_mr_files(mr_id: int) -> List[Dict[str, Any]]:
    """Получить список файлов в MR"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM mr_files WHERE mr_id = %s ORDER BY file_path", (mr_id,))
                rows = cur.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to get MR files for {mr_id}: {e}", exc_info=True)
        return []


def get_mr_comments(mr_id: int) -> List[Dict[str, Any]]:
    """Получить комментарии из оригинального ревью MR"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM mr_comments WHERE mr_id = %s ORDER BY created_at", (mr_id,))
                rows = cur.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to get MR comments for {mr_id}: {e}", exc_info=True)
        return []


def add_mr_metric(mr_id: int, metric_name: str, metric_value: float, metric_data: Optional[Dict] = None):
    """Добавить метрику для MR"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO mr_metrics (mr_id, metric_name, metric_value, metric_data)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (mr_id, metric_name) 
                    DO UPDATE SET metric_value = EXCLUDED.metric_value,
                                  metric_data = EXCLUDED.metric_data,
                                  calculated_at = CURRENT_TIMESTAMP
                """, (mr_id, metric_name, metric_value, Json(metric_data) if metric_data else None))
    except Exception as e:
        logger.error(f"Failed to add metric for MR {mr_id}: {e}", exc_info=True)


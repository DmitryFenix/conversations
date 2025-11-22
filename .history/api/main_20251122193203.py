# api/main.py
from fastapi import FastAPI, Request, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import json
import os
import shutil
import zipfile
import logging
from rq import Queue
from redis import Redis
import time
import secrets
import threading
import glob
from eval_worker import evaluate
from datetime import datetime, timedelta, timezone

# === PDF ===
from weasyprint import HTML


# === ЛОГИРОВАНИЕ ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === БД ===
DB_PATH = os.getenv("DB_PATH", "/app/reviews.db")
# Создаём директорию для БД если её нет
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)
SESSION_RETENTION_DAYS = int(os.getenv("SESSION_RETENTION_DAYS", "2"))
SESSION_CLEANUP_INTERVAL_SECONDS = int(os.getenv("SESSION_CLEANUP_INTERVAL_SECONDS", "3600"))
SESSION_RETENTION_DELTA = timedelta(days=SESSION_RETENTION_DAYS)

# === Прогресс создания сессий ===
# Храним прогресс создания сессий: session_id -> {"progress": 0-100, "message": "..."}
session_creation_progress = {}
progress_lock = threading.Lock()

def update_progress(session_id: int, progress: int, message: str = ""):
    """Обновить прогресс создания сессии"""
    with progress_lock:
        session_creation_progress[session_id] = {
            "progress": min(100, max(0, progress)),
            "message": message,
            "timestamp": time.time()
        }

def get_progress(session_id: int):
    """Получить текущий прогресс создания сессии"""
    with progress_lock:
        return session_creation_progress.get(session_id, {"progress": 0, "message": "Неизвестно", "timestamp": 0})

# === PostgreSQL для Merge Requests ===
try:
    # Добавляем текущую директорию в путь для импорта
    import sys
    import os
    if os.path.dirname(__file__) not in sys.path:
        sys.path.insert(0, os.path.dirname(__file__))
    
    from mr_database import init_mr_database, init_connection_pool
    # Инициализируем пул соединений при старте
    init_connection_pool()
    # Инициализируем структуру БД
    init_mr_database()
    logger.info("MR database module loaded successfully")
except ImportError as e:
    logger.warning(f"MR database module not available (ImportError): {e}")
    # Продолжаем работу без MR функциональности
except Exception as e:
    logger.warning(f"MR database module not available: {e}", exc_info=True)
    # Продолжаем работу без MR функциональности

# === GITEA ===
from gitea_client import GiteaClient

# Конфигурация Gitea (можно сделать через переменные окружения)
# GITEA_URL по умолчанию для доступа к Gitea в Docker контейнере
# Внутри Docker сети используем имя сервиса: http://gitea:4000
# Если Gitea на хосте - используйте http://host.docker.internal:4000
GITEA_URL = os.getenv("GITEA_URL", "http://gitea:4000")
# GITEA_WEB_URL для доступа из браузера (внешний порт)
GITEA_WEB_URL = os.getenv("GITEA_WEB_URL", "http://localhost:4001")
GITEA_ADMIN_TOKEN = os.getenv("GITEA_ADMIN_TOKEN", "")  # Будет установлен при первой настройке

# Инициализация Gitea клиента (опционально, только если токен установлен)
gitea_client = None
if GITEA_ADMIN_TOKEN:
    try:
        gitea_client = GiteaClient(GITEA_URL, GITEA_ADMIN_TOKEN)
        logger.info(f"Gitea client initialized: {GITEA_URL}")
    except Exception as e:
        logger.warning(f"Failed to initialize Gitea client: {e}")
        gitea_client = None
else:
    logger.info("Gitea client not initialized (no admin token)")


def init_db():
    global DB_PATH
    
    # Убеждаемся, что директория для БД существует
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created DB directory: {db_dir}")
        except Exception as e:
            logger.warning(f"Could not create DB directory {db_dir}: {e}")
            # Пробуем использовать /tmp как fallback
            fallback_dir = "/tmp"
            if not os.path.exists(fallback_dir):
                os.makedirs(fallback_dir, exist_ok=True)
            DB_PATH = os.path.join(fallback_dir, "reviews.db")
            logger.info(f"Using fallback DB path: {DB_PATH}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        logger.info(f"Connected to database at {DB_PATH}")
    except sqlite3.OperationalError as e:
        logger.error(f"Failed to connect to database at {DB_PATH}: {e}")
        # Пробуем создать БД в /tmp как fallback
        fallback_path = "/tmp/reviews.db"
        logger.warning(f"Trying fallback path: {fallback_path}")
        try:
            conn = sqlite3.connect(fallback_path)
            DB_PATH = fallback_path
            logger.info(f"Using fallback DB path: {DB_PATH}")
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
            raise
    c = conn.cursor()

    # Создаём таблицу с новыми полями
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT,
            mr_package TEXT,
            comments TEXT,
            created_at TEXT,
            expires_at TEXT
        )
    ''')

    # === КРИТИЧНО: Добавляем колонки, если их нет (для старых БД) ===
    c.execute("PRAGMA table_info(sessions)")
    columns = [col[1] for col in c.fetchall()]

    if 'created_at' not in columns:
        c.execute("ALTER TABLE sessions ADD COLUMN created_at TEXT")
        print("Added column: created_at")

    if 'expires_at' not in columns:
        c.execute("ALTER TABLE sessions ADD COLUMN expires_at TEXT")
        print("Added column: expires_at")

    # === Поля для разделения ролей ===
    if 'access_token' not in columns:
        # SQLite не поддерживает добавление UNIQUE колонки напрямую
        # Добавляем без UNIQUE, затем заполняем NULL значения и создаём индекс
        c.execute("ALTER TABLE sessions ADD COLUMN access_token TEXT")
        # Заполняем NULL значения для существующих записей уникальными токенами
        c.execute("SELECT id FROM sessions WHERE access_token IS NULL")
        null_rows = c.fetchall()
        for row in null_rows:
            session_id = row[0]
            token = secrets.token_urlsafe(32)
            c.execute("UPDATE sessions SET access_token = ? WHERE id = ?", (token, session_id))
        # Создаём уникальный индекс
        try:
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_access_token ON sessions(access_token)")
        except sqlite3.OperationalError as e:
            # Индекс может уже существовать или быть невозможным из-за дубликатов
            logger.warning(f"Could not create unique index on access_token: {e}")
        print("Added column: access_token")
    
    if 'reviewer_token' not in columns:
        c.execute("ALTER TABLE sessions ADD COLUMN reviewer_token TEXT")
        print("Added column: reviewer_token")
    
    if 'reviewer_name' not in columns:
        c.execute("ALTER TABLE sessions ADD COLUMN reviewer_name TEXT")
        print("Added column: reviewer_name")
    
    if 'candidate_name' not in columns:
        c.execute("ALTER TABLE sessions ADD COLUMN candidate_name TEXT")
        print("Added column: candidate_name")
    
    if 'status' not in columns:
        c.execute("ALTER TABLE sessions ADD COLUMN status TEXT DEFAULT 'active'")
        print("Added column: status")
    
    # === Поля для Gitea интеграции ===
    if 'gitea_user' not in columns:
        c.execute("ALTER TABLE sessions ADD COLUMN gitea_user TEXT")
        print("Added column: gitea_user")
    
    if 'gitea_repo' not in columns:
        c.execute("ALTER TABLE sessions ADD COLUMN gitea_repo TEXT")
        print("Added column: gitea_repo")
    
    if 'gitea_pr_id' not in columns:
        c.execute("ALTER TABLE sessions ADD COLUMN gitea_pr_id INTEGER")
        print("Added column: gitea_pr_id")
    
    if 'gitea_enabled' not in columns:
        c.execute("ALTER TABLE sessions ADD COLUMN gitea_enabled INTEGER DEFAULT 0")
        print("Added column: gitea_enabled")
    
    # === Поле для soft delete ===
    if 'deleted_at' not in columns:
        c.execute("ALTER TABLE sessions ADD COLUMN deleted_at TEXT")
        print("Added column: deleted_at")
    
    # === Поле для готовности кандидата ===
    if 'candidate_ready_at' not in columns:
        c.execute("ALTER TABLE sessions ADD COLUMN candidate_ready_at TEXT")
    
    # Добавляем поле для связи с Merge Request (если ещё не добавлено)
    try:
        c.execute("ALTER TABLE sessions ADD COLUMN mr_id INTEGER")
        conn.commit()
        logger.info("Added mr_id column to sessions table")
    except sqlite3.OperationalError:
        # Колонка уже существует
        pass
        print("Added column: candidate_ready_at")

    conn.commit()
    conn.close()


def parse_iso_datetime(value: str):
    if not value:
        return None
    try:
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        return datetime.fromisoformat(value)
    except ValueError:
        logger.warning(f"Failed to parse datetime value: {value}")
        return None


def cleanup_session_artifacts(session_ids):
    for session_id in session_ids:
        pattern = f"/artifacts/{session_id}_*"
        for path in glob.glob(pattern):
            try:
                os.remove(path)
                logger.info(f"Removed artifact file {path} for session {session_id}")
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.warning(f"Failed to remove artifact {path}: {e}")


def cleanup_old_sessions_once():
    cutoff = datetime.utcnow() - SESSION_RETENTION_DELTA
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, created_at FROM sessions WHERE deleted_at IS NULL")
    rows = c.fetchall()
    conn.close()

    expired_ids = []
    for session_id, created_at in rows:
        created_dt = parse_iso_datetime(created_at)
        if created_dt is None:
            expired_ids.append(session_id)
            continue
        
        # Приводим к naive datetime для сравнения (убираем timezone если есть)
        if created_dt.tzinfo is not None:
            # Конвертируем aware datetime в UTC, затем убираем timezone info
            created_dt = created_dt.astimezone(timezone.utc).replace(tzinfo=None)
        
        if created_dt < cutoff:
            expired_ids.append(session_id)

    if not expired_ids:
        return 0

    deleted_at = datetime.utcnow().isoformat() + 'Z'
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executemany("UPDATE sessions SET deleted_at = ? WHERE id = ?", [(deleted_at, session_id) for session_id in expired_ids])
    conn.commit()
    conn.close()

    cleanup_session_artifacts(expired_ids)
    logger.info(f"Auto-cleaned {len(expired_ids)} sessions older than {SESSION_RETENTION_DAYS} days")
    return len(expired_ids)


def start_session_cleanup_task():
    def _worker():
        while True:
            try:
                cleanup_old_sessions_once()
            except Exception as e:
                logger.error(f"Session cleanup failed: {e}", exc_info=True)
            time.sleep(max(SESSION_CLEANUP_INTERVAL_SECONDS, 60))

    threading.Thread(target=_worker, daemon=True, name="session-cleanup").start()


init_db()
start_session_cleanup_task()

# === Redis + RQ ===
# Ленивое подключение к Redis (при первом использовании)
_redis_conn = None
_queue = None

def get_redis_connection():
    """Получить подключение к Redis с retry логикой"""
    import time
    max_retries = 5
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            conn = Redis(host='redis', port=6379, socket_connect_timeout=2)
            conn.ping()
            return conn
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}, retrying...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to Redis after {max_retries} attempts: {e}")
                raise

def get_queue():
    """Получить очередь RQ (ленивая инициализация)"""
    global _redis_conn, _queue
    if _queue is None:
        if _redis_conn is None:
            _redis_conn = get_redis_connection()
        _queue = Queue(connection=_redis_conn)
    return _queue

# Для обратной совместимости создаём объекты, которые инициализируются при первом использовании
class LazyRedis:
    def __init__(self):
        self._conn = None
    
    def __getattr__(self, name):
        if self._conn is None:
            self._conn = get_redis_connection()
        return getattr(self._conn, name)

class LazyQueue:
    def __init__(self):
        self._queue = None
    
    def enqueue(self, *args, **kwargs):
        if self._queue is None:
            self._queue = get_queue()
        return self._queue.enqueue(*args, **kwargs)
    
    def __getattr__(self, name):
        if self._queue is None:
            self._queue = get_queue()
        return getattr(self._queue, name)

redis_conn = LazyRedis()
queue = LazyQueue()

# === FastAPI ===
app = FastAPI()

# === Healthcheck endpoint (для Railway и других платформ) ===
@app.get("/health")
@app.get("/api/health")
def healthcheck():
    """Простой healthcheck endpoint, не требует БД или Redis"""
    return {"status": "ok", "service": "code-review-platform"}

# === API: Ручная очистка старых сессий ===
@app.post("/api/admin/cleanup-sessions")
def manual_cleanup_sessions():
    """
    Ручной запуск очистки старых сессий (старше SESSION_RETENTION_DAYS дней)
    Полезно для немедленной очистки или тестирования
    """
    try:
        deleted_count = cleanup_old_sessions_once()
        return {
            "status": "success",
            "deleted_sessions": deleted_count,
            "retention_days": SESSION_RETENTION_DAYS,
            "message": f"Cleaned up {deleted_count} sessions older than {SESSION_RETENTION_DAYS} days"
        }
    except Exception as e:
        logger.error(f"Manual cleanup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

# === API: Статистика сессий ===
@app.get("/api/admin/sessions-stats")
def get_sessions_stats():
    """
    Получить статистику по сессиям (активные, удалённые, истекающие)
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Активные сессии
    c.execute("SELECT COUNT(*) FROM sessions WHERE deleted_at IS NULL")
    active_count = c.fetchone()[0]
    
    # Удалённые сессии
    c.execute("SELECT COUNT(*) FROM sessions WHERE deleted_at IS NOT NULL")
    deleted_count = c.fetchone()[0]
    
    # Сессии, которые скоро истекут (менее 1 часа)
    cutoff = datetime.utcnow() + timedelta(hours=1)
    cutoff_str = cutoff.isoformat() + 'Z'
    c.execute("SELECT COUNT(*) FROM sessions WHERE deleted_at IS NULL AND expires_at < ?", (cutoff_str,))
    expiring_soon_count = c.fetchone()[0]
    
    # Сессии старше retention периода, но ещё не удалённые
    retention_cutoff = datetime.utcnow() - SESSION_RETENTION_DELTA
    retention_cutoff_str = retention_cutoff.isoformat() + 'Z'
    c.execute("SELECT COUNT(*) FROM sessions WHERE deleted_at IS NULL AND created_at < ?", (retention_cutoff_str,))
    old_uncleaned_count = c.fetchone()[0]
    
    conn.close()
    
    return {
        "active_sessions": active_count,
        "deleted_sessions": deleted_count,
        "expiring_soon": expiring_soon_count,
        "old_uncleaned": old_uncleaned_count,
        "retention_days": SESSION_RETENTION_DAYS,
        "cleanup_interval_seconds": SESSION_CLEANUP_INTERVAL_SECONDS
    }

# === RQ Monitoring (должен быть ПЕРЕД статикой и catch-all) ===
_rq_router_enabled = False
try:
    logger.info("Attempting to import rq_dashboard...")
    from rq_dashboard import router as rq_router
    logger.info(f"Router imported: prefix={rq_router.prefix}, routes count={len(rq_router.routes)}")
    
    app.include_router(rq_router)
    _rq_router_enabled = True
    
    # Проверяем, что роутер действительно подключён
    all_routes = []
    for r in app.routes:
        if hasattr(r, 'path'):
            all_routes.append(r.path)
        elif hasattr(r, 'routes'):  # Для роутеров
            for sub_r in r.routes:
                if hasattr(sub_r, 'path'):
                    all_routes.append(sub_r.path)
    
    rq_routes = [r for r in all_routes if '/api/rq' in r]
    logger.info(f"RQ monitoring dashboard enabled at /api/rq/*")
    logger.info(f"RQ routes registered: {rq_routes}")
    
    if not rq_routes:
        logger.error("WARNING: No RQ routes found after registration!")
        
except ImportError as e:
    logger.error(f"Failed to import RQ dashboard (module not found): {e}")
    import traceback
    logger.error(traceback.format_exc())
except Exception as e:
    logger.error(f"Failed to enable RQ monitoring: {e}", exc_info=True)
    import traceback
    logger.error(traceback.format_exc())

# === СТАТИКА ===
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")
app.mount("/artifacts", StaticFiles(directory="/artifacts"), name="artifacts")

@app.get("/api/artifacts/{filename}")
def get_artifact(filename: str):
    file_path = f"/artifacts/{filename}"
    if not os.path.exists(file_path):
        # Для report.txt возвращаем пустой ответ вместо 404 (файл может быть еще не создан)
        if filename.endswith('_report.txt'):
            from fastapi.responses import Response
            return Response(content="Отчёт ещё не готов...", media_type="text/plain; charset=utf-8")
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

# === HTML шаблоны ===
templates = Jinja2Templates(directory="static")

# === Утилиты ===
def generate_access_token() -> str:
    """Генерирует безопасный токен для доступа кандидата"""
    return secrets.token_urlsafe(32)

def generate_reviewer_token() -> str:
    """Генерирует токен для проверяющего"""
    return secrets.token_urlsafe(24)

# === Модели ===
class SessionCreate(BaseModel):
    candidate_id: str
    mr_package: str

class ReviewerSessionCreate(BaseModel):
    candidate_name: str
    mr_package: str
    reviewer_name: str = "Reviewer"
    mr_id: Optional[int] = None  # ID Merge Request для использования в сессии (для обратной совместимости)
    mr_ids: Optional[List[int]] = None  # Список ID MR для использования в сессии (если несколько)

# === API: Создать сессию (старый endpoint для обратной совместимости) ===
@app.post("/api/sessions")
def create_session(payload: SessionCreate):
    logger.info(f"Creating session for candidate_id={payload.candidate_id}, mr_package={payload.mr_package}")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    now = datetime.utcnow()
    expires_at = now + timedelta(hours=2)
    access_token = generate_access_token()
    reviewer_token = generate_reviewer_token()

    c.execute(
        "INSERT INTO sessions (candidate_id, mr_package, comments, created_at, expires_at, access_token, reviewer_token, candidate_name, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (payload.candidate_id, payload.mr_package, json.dumps([]), now.isoformat() + 'Z', expires_at.isoformat() + 'Z', access_token, reviewer_token, payload.candidate_id, 'active')
    )
    session_id = c.lastrowid
    conn.commit()
    conn.close()

    # Создаём demo diff (для обратной совместимости)
    artifacts_dir = "/artifacts"
    if not os.path.exists(artifacts_dir):
        os.makedirs(artifacts_dir, exist_ok=True)
    
    diff_path = f"{artifacts_dir}/{session_id}_diff.patch"
    demo_diff = """diff --git a/main.py b/main.py
index abc123..def456 100644
--- a/main.py
+++ b/main.py
@@ -1,5 +1,6 @@
 def greet():
-    print("Hi")
+    print("Hello, secure world!")
+    # TODO: add input validation
     return True
"""
    try:
        with open(diff_path, "w") as f:
            f.write(demo_diff)
    except Exception as e:
        logger.warning(f"Failed to create demo diff: {e}")

    return {"session_id": session_id, "access_token": access_token, "reviewer_token": reviewer_token}

# === REVIEWER API ===
# === API: Reviewer - Создать сессию ===
@app.post("/api/reviewer/sessions")
def reviewer_create_session(payload: ReviewerSessionCreate):
    logger.info(f"Reviewer creating session for candidate={payload.candidate_name}, reviewer={payload.reviewer_name}")
    
    # Инициализируем прогресс (будем обновлять по мере создания)
    # Сначала создадим сессию, чтобы получить session_id
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    now = datetime.utcnow()
    expires_at = now + timedelta(hours=2)
    access_token = generate_access_token()  # Для кандидата
    reviewer_token = generate_reviewer_token()  # Для проверяющего

    # Генерируем имена для Gitea (транслитерация кириллицы)
    def transliterate(text):
        """Простая транслитерация кириллицы в латиницу"""
        trans_dict = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
            'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
        }
        result = ''
        for char in text:
            result += trans_dict.get(char, char if char.isalnum() or char in ['_', '-'] else '_')
        return result
    
    # Нормализация имени кандидата для Gitea username
    candidate_id_safe = transliterate(payload.candidate_name).lower()
    # Заменяем все недопустимые символы на подчёркивания
    candidate_id_safe = ''.join(c if c.isalnum() or c in ['_', '-'] else '_' for c in candidate_id_safe)
    # Убираем множественные подчёркивания
    while '__' in candidate_id_safe:
        candidate_id_safe = candidate_id_safe.replace('__', '_')
    # Убираем подчёркивания в начале и конце
    candidate_id_safe = candidate_id_safe.strip('_')
    # Если пусто или слишком короткое, используем hash
    if not candidate_id_safe or len(candidate_id_safe) < 2:
        candidate_id_safe = f"candidate_{abs(hash(payload.candidate_name)) % 10000}"
    
    gitea_user = f"candidate_{candidate_id_safe}"
    gitea_repo = None
    gitea_pr_id = None
    gitea_enabled = 0

    # Сначала всегда создаём сессию, чтобы получить session_id
    # Если указан mr_id или mr_ids, используем diff из MR вместо создания нового
    mr_id = getattr(payload, 'mr_id', None)
    mr_ids = getattr(payload, 'mr_ids', None) or []
    
    # Если указан mr_id, добавляем его в список
    if mr_id and mr_id not in mr_ids:
        mr_ids.append(mr_id)
    
    # Сохраняем первый mr_id для обратной совместимости
    first_mr_id = mr_ids[0] if mr_ids else mr_id
    
    c.execute(
        "INSERT INTO sessions (candidate_name, mr_package, comments, created_at, expires_at, access_token, reviewer_token, reviewer_name, status, candidate_id, gitea_user, gitea_enabled, mr_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (payload.candidate_name, payload.mr_package, json.dumps([]), now.isoformat() + 'Z', expires_at.isoformat() + 'Z', access_token, reviewer_token, payload.reviewer_name, 'active', candidate_id_safe, gitea_user if gitea_client else None, 0, first_mr_id)
    )
    session_id = c.lastrowid
    conn.commit()
    
    update_progress(session_id, 15, "Сессия создана в базе данных")
    
    # Если указаны MR, загружаем diff из них
    if mr_ids:
        try:
            from mr_database import get_merge_request
            artifacts_dir = "/artifacts"
            if not os.path.exists(artifacts_dir):
                os.makedirs(artifacts_dir, exist_ok=True)
            
            # Объединяем diff из всех выбранных MR
            combined_diff = []
            total_points = 0
            mr_titles = []
            
            for mr_id_item in mr_ids:
                mr = get_merge_request(mr_id_item)
                if mr:
                    if mr.get('diff_content'):
                        mr_title = mr.get('title', f'MR #{mr_id_item}')
                        combined_diff.append(f"\n\n=== MR #{mr_id_item}: {mr_title} ===\n")
                        combined_diff.append(f"Type: {mr.get('mr_type', 'unknown')}, Points: {mr.get('complexity_points', 3)}\n")
                        combined_diff.append(mr['diff_content'])
                        total_points += mr.get('complexity_points', 3)
                        mr_titles.append(mr_title)
            
            if combined_diff:
                diff_path = f"/artifacts/{session_id}_diff.patch"
                with open(diff_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(combined_diff))
                logger.info(f"Loaded diff from {len(mr_ids)} MR(s) (total {total_points} points): {', '.join(mr_titles[:3])}")
        except Exception as e:
            logger.warning(f"Failed to load diff from MR(s): {e}", exc_info=True)
    
    # Интеграция с Gitea (если клиент инициализирован)
    gitea_clone_url = None
    if gitea_client:
        try:
            update_progress(session_id, 25, "Создание пользователя Gitea...")
            # 1. Создаём пользователя для кандидата (или используем существующего)
            candidate_email = f"{gitea_user}@code-review.local"
            user_result = gitea_client.create_user(
                username=gitea_user,
                email=candidate_email
            )
            
            # Пользователь создан или уже существует - продолжаем в любом случае
            if user_result:
                logger.info(f"Created Gitea user: {gitea_user}")
            else:
                # Проверяем, может пользователь уже существует (это нормально)
                # Это не ошибка - просто продолжаем использовать существующего пользователя
                logger.info(f"Gitea user may already exist: {gitea_user}, continuing...")
            
            # Продолжаем создание репозитория даже если пользователь уже существует
            
            update_progress(session_id, 40, "Создание репозитория Gitea...")
            # Теперь создаём репозиторий с session_id
            gitea_repo = f"session_{session_id}"
            repo_result = gitea_client.create_repository(
                owner=gitea_user,
                repo_name=gitea_repo,
                description=f"Code review session for {payload.candidate_name}",
                private=True
            )
            
            if repo_result:
                logger.info(f"Created Gitea repository: {gitea_user}/{gitea_repo}")
                update_progress(session_id, 55, "Репозиторий создан, создание ветки...")
                
                # Минимальная задержка для инициализации репозитория
                import time
                time.sleep(0.3)  # Уменьшили до 0.3 секунды
                
                # 3. Создаём ветку для кандидата сразу
                candidate_branch = f"candidate-work-{session_id}"
                branch_result = gitea_client.create_branch(
                    owner=gitea_user,
                    repo=gitea_repo,
                    branch_name=candidate_branch,
                    from_branch="main"
                )
                
                if not branch_result:
                    # Если не получилось создать ветку, пробуем создать файл в main
                    logger.warning(f"Failed to create branch {candidate_branch}, trying main branch")
                    candidate_branch = "main"
                
                update_progress(session_id, 70, "Создание начального файла...")
                # Создаём файл сразу в нужной ветке (candidate-work-{id} или main)
                starting_code = f"""# Code Review Session #{session_id}
# Candidate: {payload.candidate_name}

def greet():
    print("Hi")
    return True
"""
                # Пытаемся создать файл с быстрыми повторными попытками
                file_result = None
                for attempt in range(2):  # Уменьшили до 2 попыток
                    file_result = gitea_client.create_file(
                        owner=gitea_user,
                        repo=gitea_repo,
                        file_path="main.py",
                        content=starting_code,
                        message=f"Code review session #{session_id} - candidate work",
                        branch=candidate_branch,
                        new_branch=True
                    )
                    if file_result:
                        break
                    if attempt < 1:
                        time.sleep(0.5)  # Быстрая задержка: 0.5 сек вместо 2, 4
                        logger.info(f"Retrying file creation (attempt {attempt + 2}/2)...")
                
                if file_result:
                    gitea_enabled = 1
                    gitea_clone_url = gitea_client.get_repository_clone_url(gitea_user, gitea_repo)
                    logger.info(f"Initialized starting code in repository (branch: {candidate_branch})")
                    
                    # Обновляем сессию с данными Gitea
                    c.execute(
                        "UPDATE sessions SET gitea_repo = ?, gitea_enabled = ? WHERE id = ?",
                        (gitea_repo, gitea_enabled, session_id)
                    )
                    conn.commit()
                    
                    update_progress(session_id, 85, "Создание Pull Request...")
                    # Автоматически создаём PR (файл уже в нужной ветке)
                    try:
                        logger.info(f"Creating PR for session {session_id}")
                        # Минимальная задержка для синхронизации Gitea
                        time.sleep(0.3)
                        
                        # Создаём PR из ветки кандидата в main
                        pr_title = f"Code Review Session #{session_id} - {payload.candidate_name}"
                        pr_body = f"Code review session for candidate: {payload.candidate_name}\n\nSession ID: {session_id}\n\nThis PR contains the candidate's work for review."
                        
                        pr_result = gitea_client.create_pull_request(
                            owner=gitea_user,
                            repo=gitea_repo,
                            title=pr_title,
                            body=pr_body,
                            head=candidate_branch,
                            base="main"
                        )
                        
                        if pr_result:
                            pr_id = pr_result.get("number")
                            c.execute("UPDATE sessions SET gitea_pr_id = ? WHERE id = ?", (pr_id, session_id))
                            conn.commit()
                            logger.info(f"Created PR #{pr_id} for session {session_id}")
                        else:
                            logger.warning(f"Failed to create PR for session {session_id}")
                    except Exception as e:
                        logger.error(f"Error creating PR for session {session_id}: {e}", exc_info=True)
                        # Не прерываем создание сессии, если PR не создался
                else:
                    logger.warning(f"Failed to create initial file in repository, but repository exists")
                    # Репозиторий создан, но файл не создан - всё равно включаем интеграцию
                    gitea_enabled = 1
                    gitea_clone_url = gitea_client.get_repository_clone_url(gitea_user, gitea_repo)
                    
                    # Обновляем сессию с данными Gitea
                    c.execute(
                        "UPDATE sessions SET gitea_repo = ?, gitea_enabled = ? WHERE id = ?",
                        (gitea_repo, gitea_enabled, session_id)
                    )
                    conn.commit()
            else:
                logger.warning(f"Failed to create Gitea repository for user: {gitea_user}")
                # Репозиторий не создан - сессия уже создана без Gitea
        except Exception as e:
            logger.error(f"Error during Gitea integration: {e}", exc_info=True)
            # Если произошла ошибка, сессия уже создана без Gitea (gitea_enabled=0)
    
    # Сессия уже создана выше (с gitea_enabled=0 по умолчанию, или обновлена если Gitea успешно настроен)

    conn.close()

    update_progress(session_id, 95, "Создание артефактов...")
    # Создаём demo diff (только если не использованы MR)
    # mr_ids определён выше в функции
    if not (mr_ids or mr_id):
        artifacts_dir = "/artifacts"
        if not os.path.exists(artifacts_dir):
            os.makedirs(artifacts_dir, exist_ok=True)
        
        diff_path = f"{artifacts_dir}/{session_id}_diff.patch"
        # Проверяем, не создан ли уже diff из MR(s)
        if not os.path.exists(diff_path):
            demo_diff = """diff --git a/main.py b/main.py
index abc123..def456 100644
--- a/main.py
+++ b/main.py
@@ -1,5 +1,6 @@
 def greet():
-    print("Hi")
+    print("Hello, secure world!")
+    # TODO: add input validation
     return True
"""
            try:
                with open(diff_path, "w") as f:
                    f.write(demo_diff)
            except Exception as e:
                logger.warning(f"Failed to create demo diff: {e}")

    update_progress(session_id, 100, "Готово!")
    
    response = {
        "session_id": session_id,
        "access_token": access_token,
        "reviewer_token": reviewer_token,
        "candidate_url": f"/candidate/{access_token}",
        "reviewer_url": f"/reviewer/sessions/{session_id}"
    }
    
    # Добавляем информацию о Gitea если она доступна
    if gitea_enabled and gitea_clone_url:
        response["gitea"] = {
            "enabled": True,
            "user": gitea_user,
            "repo": gitea_repo,
            "clone_url": gitea_clone_url,
            "web_url": f"{GITEA_WEB_URL}/{gitea_user}/{gitea_repo}"
        }
    
    # Удаляем прогресс через 5 секунд после завершения
    def cleanup_progress():
        time.sleep(5)
        with progress_lock:
            session_creation_progress.pop(session_id, None)
    
    threading.Thread(target=cleanup_progress, daemon=True).start()
    
    return response

# === API: Получить прогресс создания сессии ===
@app.get("/api/reviewer/sessions/{session_id}/creation-progress")
def get_session_creation_progress(session_id: int):
    """Получить текущий прогресс создания сессии"""
    progress_data = get_progress(session_id)
    return {
        "session_id": session_id,
        "progress": progress_data["progress"],
        "message": progress_data["message"],
        "timestamp": progress_data["timestamp"]
    }

# === API: Merge Requests ===
try:
    from mr_database import (
        get_merge_request, list_merge_requests, search_merge_requests,
        get_mr_files, get_mr_comments
    )
    
    @app.get("/api/mr/list")
    def mr_list(
        language: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        change_type: Optional[str] = None,
        min_complexity: Optional[float] = None,
        max_complexity: Optional[float] = None,
        mr_type: Optional[str] = None,
        min_complexity_points: Optional[int] = None,
        max_complexity_points: Optional[int] = None,
        stack_tag: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ):
        """Получить список MR с фильтрацией"""
        stack_tags = [stack_tag] if stack_tag else None
        mrs = list_merge_requests(
            language=language,
            difficulty_level=difficulty_level,
            change_type=change_type,
            min_complexity=min_complexity,
            max_complexity=max_complexity,
            mr_type=mr_type,
            min_complexity_points=min_complexity_points,
            max_complexity_points=max_complexity_points,
            stack_tags=stack_tags,
            limit=limit,
            offset=offset
        )
        return {"merge_requests": mrs, "total": len(mrs)}
    
    @app.get("/api/mr/recommend")
    def mr_recommend(
        target_grade: str,  # junior, middle, senior
        stack_tags: Optional[str] = None,  # Через запятую: "python,backend"
        target_points: Optional[int] = None,  # Целевое количество баллов
        mr_types: Optional[str] = None  # Через запятую: "bugfix,feature"
    ):
        """
        Рекомендации MR для кандидата
        
        Args:
            target_grade: junior (3-4 балла), middle (5-7), senior (8-10)
            stack_tags: Теги стека через запятую
            target_points: Целевое количество баллов (опционально)
            mr_types: Типы MR через запятую (опционально)
        """
        # Определяем целевой диапазон баллов
        grade_ranges = {
            'junior': (3, 4),
            'middle': (5, 7),
            'senior': (8, 10)
        }
        
        min_points, max_points = grade_ranges.get(target_grade.lower(), (5, 7))
        if target_points:
            min_points = max(1, target_points - 1)
            max_points = target_points + 1
        
        # Парсим теги стека
        stack_tags_list = None
        if stack_tags:
            stack_tags_list = [tag.strip() for tag in stack_tags.split(',')]
        
        # Парсим типы MR
        mr_types_list = None
        if mr_types:
            mr_types_list = [t.strip() for t in mr_types.split(',')]
        
        # Получаем все подходящие MR
        all_mrs = list_merge_requests(
            stack_tags=stack_tags_list,
            limit=100  # Достаточно для подбора
        )
        
        # Фильтруем по типам если указаны
        if mr_types_list:
            all_mrs = [mr for mr in all_mrs if mr.get('mr_type') in mr_types_list]
        
        # Сортируем по баллам сложности
        all_mrs.sort(key=lambda x: x.get('complexity_points', 3))
        
        # Подбираем набор MR для достижения целевого диапазона баллов
        selected_mrs = []
        total_points = 0
        
        for mr in all_mrs:
            points = mr.get('complexity_points', 3)
            if total_points + points <= max_points:
                selected_mrs.append(mr)
                total_points += points
                if total_points >= min_points:
                    break
        
        return {
            "recommended_mrs": selected_mrs,
            "total_points": total_points,
            "target_range": f"{min_points}-{max_points}",
            "grade": target_grade
        }
    
    @app.get("/api/mr/{mr_id}")
    def mr_get(mr_id: int):
        """Получить детали MR"""
        mr = get_merge_request(mr_id)
        if not mr:
            raise HTTPException(status_code=404, detail="Merge Request not found")
        return mr
    
    @app.get("/api/mr/{mr_id}/diff")
    def mr_get_diff(mr_id: int):
        """Получить diff MR"""
        mr = get_merge_request(mr_id)
        if not mr:
            raise HTTPException(status_code=404, detail="Merge Request not found")
        
        diff_content = mr.get('diff_content')
        if not diff_content:
            # Пробуем загрузить из файла
            diff_path = mr.get('diff_path')
            if diff_path and os.path.exists(diff_path):
                with open(diff_path, 'r', encoding='utf-8') as f:
                    diff_content = f.read()
            else:
                raise HTTPException(status_code=404, detail="Diff not found")
        
        from fastapi.responses import Response
        return Response(content=diff_content, media_type="text/plain; charset=utf-8")
    
    @app.get("/api/mr/{mr_id}/files")
    def mr_get_files(mr_id: int):
        """Получить список файлов в MR"""
        files = get_mr_files(mr_id)
        return {"files": files}
    
    @app.get("/api/mr/{mr_id}/comments")
    def mr_get_comments(mr_id: int):
        """Получить комментарии из оригинального ревью MR"""
        comments = get_mr_comments(mr_id)
        return {"comments": comments}
    
    @app.get("/api/mr/search")
    def mr_search(q: str, limit: int = 50):
        """Полнотекстовый поиск по MR"""
        mrs = search_merge_requests(q, limit=limit)
        return {"merge_requests": mrs, "total": len(mrs)}
    
    @app.put("/api/reviewer/sessions/{session_id}/mrs")
    def update_session_mrs(session_id: int, payload: dict):
        """Обновить выбранные MR для сессии"""
        mr_ids = payload.get('mr_ids', [])
        
        if not mr_ids:
            # Удаляем MR из сессии
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("UPDATE sessions SET mr_id = NULL WHERE id = ?", (session_id,))
            conn.commit()
            conn.close()
            return {"message": "MR removed from session"}
        
        # Сохраняем первый mr_id для обратной совместимости
        first_mr_id = mr_ids[0]
        
        # Обновляем сессию
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE sessions SET mr_id = ? WHERE id = ?", (first_mr_id, session_id))
        conn.commit()
        conn.close()
        
        # Загружаем diff из выбранных MR
        try:
            artifacts_dir = "/artifacts"
            if not os.path.exists(artifacts_dir):
                os.makedirs(artifacts_dir, exist_ok=True)
            
            # Объединяем diff из всех выбранных MR
            combined_diff = []
            total_points = 0
            mr_titles = []
            
            for mr_id_item in mr_ids:
                mr = get_merge_request(mr_id_item)
                if mr:
                    if mr.get('diff_content'):
                        mr_title = mr.get('title', f'MR #{mr_id_item}')
                        combined_diff.append(f"\n\n=== MR #{mr_id_item}: {mr_title} ===\n")
                        combined_diff.append(f"Type: {mr.get('mr_type', 'unknown')}, Points: {mr.get('complexity_points', 3)}\n")
                        combined_diff.append(mr['diff_content'])
                        total_points += mr.get('complexity_points', 3)
                        mr_titles.append(mr_title)
            
            if combined_diff:
                diff_path = f"/artifacts/{session_id}_diff.patch"
                with open(diff_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(combined_diff))
                logger.info(f"Updated diff from {len(mr_ids)} MR(s) (total {total_points} points) for session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to update diff from MR(s): {e}", exc_info=True)
        
        return {
            "message": "MR updated successfully",
            "mr_ids": mr_ids,
            "total_points": total_points
        }
    
    logger.info("MR API endpoints registered")
    
except ImportError:
    logger.warning("MR database module not available, MR endpoints disabled")

# === API: Reviewer - Список сессий ===
@app.get("/api/reviewer/sessions")
def reviewer_list_sessions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Показываем только не удалённые сессии
    c.execute("SELECT id, candidate_name, reviewer_name, created_at, expires_at, status, gitea_user, gitea_repo, gitea_pr_id, gitea_enabled, comments, candidate_ready_at FROM sessions WHERE deleted_at IS NULL ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    
    sessions = []
    for row in rows:
        session_data = {
            "id": row[0],
            "candidate_name": row[1] or "Unknown",
            "reviewer_name": row[2] or "Unknown",
            "created_at": row[3],
            "expires_at": row[4],
            "status": row[5] or "active",
            "comments": json.loads(row[10]) if len(row) > 10 and row[10] else [],
            "candidate_ready_at": row[11] if len(row) > 11 else None
        }
        
        # Добавляем информацию о Gitea если она доступна
        if len(row) > 9 and row[9]:  # gitea_enabled
            session_data["gitea"] = {
                "enabled": True,
                "user": row[6],  # gitea_user
                "repo": row[7],  # gitea_repo
                "pr_id": row[8],  # gitea_pr_id
                "web_url": f"{GITEA_WEB_URL}/{row[6]}/{row[7]}" if row[6] and row[7] else None
            }
        
        sessions.append(session_data)
    
    return {"sessions": sessions}

# === API: Reviewer - Удалить сессию ===
@app.delete("/api/reviewer/sessions/{session_id}")
def reviewer_delete_session(session_id: int):
    """
    Удалить сессию (soft delete - помечаем как удалённую)
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Проверяем, что сессия существует и не удалена
    c.execute("SELECT id, deleted_at FROM sessions WHERE id = ?", (session_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
    
    if row[1]:  # deleted_at уже установлен
        conn.close()
        raise HTTPException(status_code=400, detail="Session already deleted")
    
    # Soft delete - помечаем как удалённую
    deleted_at = datetime.utcnow().isoformat() + 'Z'
    c.execute("UPDATE sessions SET deleted_at = ? WHERE id = ?", (deleted_at, session_id))
    conn.commit()
    conn.close()
    
    logger.info(f"Session {session_id} marked as deleted")
    return {"status": "deleted", "session_id": session_id, "deleted_at": deleted_at}

# === API: Reviewer - Завершить сессию досрочно ===
@app.post("/api/reviewer/sessions/{session_id}/finish")
def reviewer_finish_session(session_id: int):
    """
    Завершить сессию досрочно (установить expires_at на текущее время)
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Проверяем, что сессия существует
    c.execute("SELECT id, expires_at, deleted_at FROM sessions WHERE id = ?", (session_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
    
    if row[2]:  # deleted_at уже установлен
        conn.close()
        raise HTTPException(status_code=400, detail="Session already deleted")
    
    # Устанавливаем expires_at на текущее время
    finished_at = datetime.utcnow().isoformat() + 'Z'
    c.execute("UPDATE sessions SET expires_at = ?, status = 'finished' WHERE id = ?", (finished_at, session_id))
    conn.commit()
    conn.close()
    
    logger.info(f"Session {session_id} finished early by reviewer")
    return {"status": "finished", "session_id": session_id, "finished_at": finished_at}

# === API: Reviewer - Получить сессию ===
@app.get("/api/reviewer/sessions/{session_id}")
def reviewer_get_session(session_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Показываем сессию даже если она удалена (для просмотра истории)
    c.execute("SELECT id, candidate_name, reviewer_name, mr_package, comments, created_at, expires_at, status, access_token, gitea_user, gitea_repo, gitea_pr_id, gitea_enabled, deleted_at, candidate_ready_at, mr_id FROM sessions WHERE id = ?", (session_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    
    created_at = row[5] if row[5] else datetime.utcnow().isoformat() + 'Z'
    expires_at = row[6] if row[6] else (datetime.utcnow() + timedelta(hours=2)).isoformat() + 'Z'
    
    if created_at and not created_at.endswith('Z') and '+' not in created_at:
        created_at = created_at + 'Z'
    if expires_at and not expires_at.endswith('Z') and '+' not in expires_at:
        expires_at = expires_at + 'Z'
    
    response = {
        "id": row[0],
        "candidate_name": row[1],
        "reviewer_name": row[2],
        "mr_package": row[3],
        "comments": json.loads(row[4]) if row[4] else [],
        "created_at": created_at,
        "expires_at": expires_at,
        "status": row[7] or "active",
        "access_token": row[8],  # Токен для кандидата
        "deleted_at": row[13] if len(row) > 13 else None,  # deleted_at
        "candidate_ready_at": row[14] if len(row) > 14 else None,  # candidate_ready_at
        "mr_id": row[15] if len(row) > 15 else None  # mr_id
    }
    
    # Добавляем информацию о Gitea если она доступна
    if row[12]:  # gitea_enabled
        response["gitea"] = {
            "enabled": True,
            "user": row[9],  # gitea_user
            "repo": row[10],  # gitea_repo
            "pr_id": row[11],  # gitea_pr_id
            "web_url": f"{GITEA_WEB_URL}/{row[9]}/{row[10]}" if row[9] and row[10] else None
        }
    
    # Информация о Merge Request (если привязан)
    if response.get("mr_id"):
        try:
            from mr_database import get_merge_request
            mr = get_merge_request(response["mr_id"])
            if mr:
                response["merge_request"] = {
                    "id": mr["id"],
                    "title": mr.get("title"),
                    "language": mr.get("language"),
                    "difficulty_level": mr.get("difficulty_level"),
                    "change_type": mr.get("change_type"),
                    "complexity_score": mr.get("complexity_score")
                }
        except Exception as e:
            logger.warning(f"Failed to load MR info for session {session_id}: {e}")
    
    return response

# === API: Получить сессию ===
@app.get("/api/sessions/{session_id}")
def get_session(session_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, candidate_id, mr_package, comments, created_at, expires_at FROM sessions WHERE id = ?", (session_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Fallback для старых сессий без created_at/expires_at
    created_at = row[4] if row[4] else datetime.utcnow().isoformat() + 'Z'
    expires_at = row[5] if row[5] else (datetime.utcnow() + timedelta(hours=2)).isoformat() + 'Z'
    
    # Убеждаемся, что время в UTC формате (добавляем Z если его нет)
    if created_at and not created_at.endswith('Z') and '+' not in created_at:
        created_at = created_at + 'Z'
    if expires_at and not expires_at.endswith('Z') and '+' not in expires_at:
        expires_at = expires_at + 'Z'
    
    return {
        "id": row[0],
        "candidate_id": row[1],
        "mr_package": row[2],
        "comments": json.loads(row[3]),
        "created_at": created_at,
        "expires_at": expires_at
    }

@app.post("/api/upload-mr")
async def upload_mr(file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only .zip files allowed")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    now = datetime.utcnow()
    expires_at = now + timedelta(hours=2)
    access_token = generate_access_token()
    reviewer_token = generate_reviewer_token()

    c.execute(
        "INSERT INTO sessions (candidate_id, mr_package, comments, created_at, expires_at, access_token, reviewer_token, candidate_name, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (f"upload_{int(time.time())}", file.filename, json.dumps([]), now.isoformat() + 'Z', expires_at.isoformat() + 'Z', access_token, reviewer_token, f"upload_{int(time.time())}", 'active')
    )
    session_id = c.lastrowid
    conn.commit()
    conn.close()

    mr_dir = f"/artifacts/mr_{session_id}"
    os.makedirs(mr_dir, exist_ok=True)
    zip_path = f"{mr_dir}/{session_id}.zip"
    with open(zip_path, "wb") as f:
        content = await file.read()
        f.write(content)

    if not zipfile.is_zipfile(zip_path):
        os.remove(zip_path)
        raise HTTPException(status_code=400, detail="Invalid ZIP file")

    with zipfile.ZipFile(zip_path) as z:
        z.extractall(mr_dir)

    diff_path = f"/artifacts/{session_id}_diff.patch"
    with open(diff_path, "w") as f:
        f.write(f"""diff --git a/uploaded_file b/uploaded_file
index 0000000..1111111 100644
--- /dev/null
+++ b/uploaded_file
@@ -0,0 +1,1 @@
+Uploaded via /api/upload-mr
""")

    return {"session_id": session_id, "access_token": access_token, "reviewer_token": reviewer_token}

# === API: Оценка (старый endpoint для обратной совместимости) ===
@app.get("/api/sessions/{session_id}/evaluate")
def evaluate_session(session_id: int):
    # Используем оптимизированную очередь с мониторингом
    try:
        from rq_monitor import OptimizedQueue
        opt_queue = OptimizedQueue(get_redis_connection(), "default")
        job = opt_queue.enqueue_evaluation(session_id, timeout=300, retry=2, priority="normal")
        logger.info(f"Evaluation job enqueued: {job.id} for session {session_id}")
    except Exception as e:
        logger.warning(f"Failed to use optimized queue, falling back to default: {e}")
        job = queue.enqueue("eval_worker.evaluate", session_id)
    return {"job_id": job.id}

# === API: Reviewer - Запустить оценку ===
@app.post("/api/reviewer/sessions/{session_id}/evaluate")
def reviewer_evaluate_session(session_id: int):
    """
    Запустить оценку сессии (асинхронно через RQ)
    Перед оценкой автоматически синхронизируем комментарии из Gitea PR, если он существует
    """
    # Проверяем, что сессия существует
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT gitea_user, gitea_repo, gitea_pr_id FROM sessions WHERE id = ?", (session_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    
    gitea_user, gitea_repo, gitea_pr_id = row
    
    # Если есть PR, синхронизируем комментарии из Gitea перед оценкой
    if gitea_client and gitea_pr_id:
        try:
            logger.info(f"Auto-syncing comments from Gitea PR before evaluation for session {session_id}")
            reviewer_sync_comments_from_gitea(session_id)
        except Exception as e:
            logger.warning(f"Failed to sync comments from Gitea before evaluation: {e}")
            # Не прерываем оценку, если синхронизация не удалась
    
    # Используем оптимизированную очередь с мониторингом
    try:
        from rq_monitor import OptimizedQueue
        opt_queue = OptimizedQueue(get_redis_connection(), "default")
        job = opt_queue.enqueue_evaluation(
            session_id,
            timeout=300,  # 5 минут
            retry=2,  # 2 попытки
            priority="normal"
        )
        logger.info(f"Evaluation job enqueued: {job.id} for session {session_id}")
    except Exception as e:
        import traceback
        logger.warning(f"Failed to use optimized queue, falling back to default: {e}")
        logger.warning(f"Traceback: {traceback.format_exc()}")
        # Fallback на обычную очередь
        job = queue.enqueue("eval_worker.evaluate", session_id)
    
    return {"job_id": job.id}

@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    job = queue.fetch_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": job.get_status(), "result": job.result}

# === API: Добавить комментарий (старый endpoint для обратной совместимости) ===
@app.post("/api/sessions/{session_id}/comments")
def add_comment(session_id: int, comment: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT comments FROM sessions WHERE id = ?", (session_id,))
    row = c.fetchone()
    if not row:
        raise HTTPException(status_code=404)
    comments = json.loads(row[0]) if row[0] else []
    comments.append(comment)
    c.execute("UPDATE sessions SET comments = ? WHERE id = ?", (json.dumps(comments), session_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}

# === CANDIDATE API ===
# === API: Candidate - Получить сессию по токену ===
@app.get("/api/candidate/sessions/{token}")
def candidate_get_session(token: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Кандидат не может получить доступ к удалённым сессиям
    c.execute("SELECT id, candidate_name, mr_package, comments, created_at, expires_at, status, gitea_user, gitea_repo, gitea_enabled, gitea_pr_id, candidate_ready_at FROM sessions WHERE access_token = ? AND deleted_at IS NULL", (token,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Session not found or invalid token")
    
    created_at = row[4] if row[4] else datetime.utcnow().isoformat() + 'Z'
    expires_at = row[5] if row[5] else (datetime.utcnow() + timedelta(hours=2)).isoformat() + 'Z'
    
    if created_at and not created_at.endswith('Z') and '+' not in created_at:
        created_at = created_at + 'Z'
    if expires_at and not expires_at.endswith('Z') and '+' not in expires_at:
        expires_at = expires_at + 'Z'
    
    response = {
        "session_id": row[0],
        "candidate_name": row[1] or "Candidate",
        "mr_package": row[2],
        "comments": json.loads(row[3]) if row[3] else [],
        "created_at": created_at,
        "expires_at": expires_at,
        "status": row[6] or "active",
        "candidate_ready_at": row[11] if len(row) > 11 else None
    }
    
    # Добавляем информацию о Gitea если она доступна
    if row[9]:  # gitea_enabled
        gitea_user = row[7]
        gitea_repo = row[8]
        gitea_pr_id = row[10] if len(row) > 10 else None
        
        # Формируем URL репозитория
        repo_url = f"{GITEA_WEB_URL}/{gitea_user}/{gitea_repo}" if gitea_user and gitea_repo else None
        
        # Формируем URL PR, если он создан
        pr_url = None
        if gitea_pr_id and repo_url:
            pr_url = f"{repo_url}/pulls/{gitea_pr_id}"
        
        response["gitea"] = {
            "enabled": True,
            "user": gitea_user,
            "repo": gitea_repo,
            "pr_id": gitea_pr_id,
            "web_url": repo_url,
            "pr_url": pr_url  # URL для PR, если он создан
        }
    
    return response

# === API: Candidate - Получить diff ===
@app.get("/api/candidate/sessions/{token}/diff")
def candidate_get_diff(token: str):
    # Находим session_id по токену (только не удалённые сессии)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM sessions WHERE access_token = ? AND deleted_at IS NULL", (token,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_id = row[0]
    diff_path = f"/artifacts/{session_id}_diff.patch"
    
    if not os.path.exists(diff_path):
        raise HTTPException(status_code=404, detail="Diff not found")
    
    with open(diff_path, "r", encoding="utf-8") as f:
        diff_content = f.read()
    
    from fastapi.responses import Response
    return Response(content=diff_content, media_type="text/plain; charset=utf-8")

# === API: Candidate - Получить комментарии ===
@app.get("/api/candidate/sessions/{token}/comments")
def candidate_get_comments(token: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Кандидат не может получить доступ к удалённым сессиям
    c.execute("SELECT comments FROM sessions WHERE access_token = ? AND deleted_at IS NULL", (token,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    
    comments = json.loads(row[0]) if row[0] else []
    return {"comments": comments}

# === API: Candidate - Добавить комментарий ===
@app.post("/api/candidate/sessions/{token}/comments")
def candidate_add_comment(token: str, comment: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Кандидат не может добавлять комментарии к удалённым сессиям
    c.execute("SELECT comments, id FROM sessions WHERE access_token = ? AND deleted_at IS NULL", (token,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
    
    comments = json.loads(row[0]) if row[0] else []
    comments.append(comment)
    session_id = row[1]
    
    c.execute("UPDATE sessions SET comments = ? WHERE id = ?", (json.dumps(comments), session_id))
    conn.commit()
    conn.close()
    
    return {"status": "ok"}

# === API: Candidate - Отметить готовность ===
@app.post("/api/candidate/sessions/{token}/ready")
def candidate_mark_ready(token: str):
    """
    Кандидат сигнализирует о готовности (завершил code review)
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, candidate_ready_at FROM sessions WHERE access_token = ? AND deleted_at IS NULL", (token,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_id = row[0]
    already_ready = row[1]
    
    if already_ready:
        conn.close()
        return {"status": "already_ready", "ready_at": already_ready}
    
    # Отмечаем готовность
    ready_at = datetime.utcnow().isoformat() + 'Z'
    c.execute("UPDATE sessions SET candidate_ready_at = ? WHERE id = ?", (ready_at, session_id))
    conn.commit()
    conn.close()
    
    logger.info(f"Candidate marked session {session_id} as ready")
    return {"status": "ready", "ready_at": ready_at}

# === API: Продлить сессию на 30 минут (старый endpoint для обратной совместимости) ===
@app.post("/api/sessions/{session_id}/extend")
def extend_session(session_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT expires_at FROM sessions WHERE id = ?", (session_id,))
    row = c.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Получаем текущий expires_at или создаём новый
    if row[0]:
        expires_str = row[0]
        # Обрабатываем формат с Z или без него
        # Убираем Z и парсим как UTC
        if expires_str.endswith('Z'):
            expires_str = expires_str[:-1]
        try:
            current_expires = datetime.fromisoformat(expires_str)
        except ValueError:
            # Если не удалось распарсить, используем текущее время + 2 часа
            current_expires = datetime.utcnow() + timedelta(hours=2)
        
        # Если нет timezone info, считаем UTC
        if current_expires.tzinfo is not None:
            # Конвертируем в UTC naive для вычислений
            current_expires = current_expires.replace(tzinfo=None)
        
        # Проверяем, что expires_at не в прошлом (если в прошлом, используем текущее время + 2 часа)
        if current_expires < datetime.utcnow():
            current_expires = datetime.utcnow() + timedelta(hours=2)
    else:
        # Если expires_at не установлен, создаём новое время (текущее + 2 часа)
        current_expires = datetime.utcnow() + timedelta(hours=2)
    
    # Продлеваем на 30 минут от текущего expires_at
    new_expires_at = current_expires + timedelta(minutes=30)
    
    # Сохраняем новое время с Z для явного указания UTC
    expires_at_str = new_expires_at.isoformat() + 'Z'
    c.execute("UPDATE sessions SET expires_at = ? WHERE id = ?", (expires_at_str, session_id))
    conn.commit()
    conn.close()
    
    return {
        "status": "ok",
        "expires_at": expires_at_str  # Возвращаем с Z
    }

# === API: Reviewer - Продлить сессию на 30 минут ===
@app.post("/api/reviewer/sessions/{session_id}/extend")
def reviewer_extend_session(session_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT expires_at FROM sessions WHERE id = ?", (session_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
    
    if row[0]:
        expires_str = row[0]
        if expires_str.endswith('Z'):
            expires_str = expires_str[:-1]
        try:
            current_expires = datetime.fromisoformat(expires_str)
        except ValueError:
            current_expires = datetime.utcnow() + timedelta(hours=2)
        
        if current_expires.tzinfo is not None:
            current_expires = current_expires.replace(tzinfo=None)
        
        if current_expires < datetime.utcnow():
            current_expires = datetime.utcnow() + timedelta(hours=2)
    else:
        current_expires = datetime.utcnow() + timedelta(hours=2)
    
    new_expires_at = current_expires + timedelta(minutes=30)
    expires_at_str = new_expires_at.isoformat() + 'Z'
    c.execute("UPDATE sessions SET expires_at = ? WHERE id = ?", (expires_at_str, session_id))
    conn.commit()
    conn.close()
    
    return {
        "status": "ok",
        "expires_at": expires_at_str
    }

# === API: Reviewer - Создать Pull Request в Gitea ===
@app.post("/api/reviewer/sessions/{session_id}/gitea/create-pr")
def reviewer_create_gitea_pr(session_id: int, payload: dict = None):
    """
    Создать Pull Request в Gitea для сессии
    """
    if not gitea_client:
        raise HTTPException(status_code=503, detail="Gitea integration not available")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT gitea_user, gitea_repo, gitea_enabled, candidate_name FROM sessions WHERE id = ?", (session_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    
    gitea_user, gitea_repo, gitea_enabled, candidate_name = row
    
    if not gitea_enabled or not gitea_user or not gitea_repo:
        raise HTTPException(status_code=400, detail="Gitea not enabled for this session")
    
    # Создаём PR - для этого нужна ветка с изменениями
    # 1. Создаём новую ветку для изменений кандидата
    candidate_branch = f"candidate-work-{session_id}"
    branch_result = gitea_client.create_branch(
        owner=gitea_user,
        repo=gitea_repo,
        branch_name=candidate_branch,
        from_branch="main"
    )
    
    if not branch_result:
        raise HTTPException(status_code=500, detail="Failed to create candidate branch in Gitea")
    
    # 2. Обновляем файл в новой ветке, добавляя комментарий о code review
    import time
    time.sleep(0.3)  # Минимальная задержка для синхронизации Gitea
    
    # Обновляем файл в новой ветке, добавляя комментарий о code review
    # update_file сам получит SHA файла из новой ветки
    update_result = gitea_client.update_file(
        owner=gitea_user,
        repo=gitea_repo,
        file_path="main.py",
        content=f"""# Code Review Session #{session_id}
# Candidate: {candidate_name}

def greet():
    print("Hi")
    return True
""",
        message=f"Code review session #{session_id} - candidate work",
        branch=candidate_branch,
        sha=None  # Для новой ветки SHA будет получен автоматически
    )
    
    if not update_result:
        logger.warning(f"Failed to update file in branch {candidate_branch}, but branch created")
    
    # 3. Создаём PR из новой ветки в main
    pr_title = f"Code Review Session #{session_id} - {candidate_name}"
    pr_body = f"Code review session for candidate: {candidate_name}\n\nSession ID: {session_id}\n\nThis PR contains the candidate's work for review."
    
    pr_result = gitea_client.create_pull_request(
        owner=gitea_user,
        repo=gitea_repo,
        title=pr_title,
        body=pr_body,
        head=candidate_branch,  # Новая ветка с изменениями
        base="main"  # Базовая ветка
    )
    
    if not pr_result:
        raise HTTPException(status_code=500, detail="Failed to create PR in Gitea")
    
    pr_id = pr_result.get("number")
    
    # Сохраняем PR ID в БД
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE sessions SET gitea_pr_id = ? WHERE id = ?", (pr_id, session_id))
    conn.commit()
    conn.close()
    
    return {
        "status": "ok",
        "pr_id": pr_id,
        "pr_url": f"{GITEA_WEB_URL}/{gitea_user}/{gitea_repo}/pulls/{pr_id}",
        "pr_data": pr_result
    }

# === API: Reviewer - Получить Pull Request из Gitea ===
@app.get("/api/reviewer/sessions/{session_id}/gitea/pr")
def reviewer_get_gitea_pr(session_id: int):
    """
    Получить информацию о Pull Request из Gitea
    """
    if not gitea_client:
        raise HTTPException(status_code=503, detail="Gitea integration not available")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT gitea_user, gitea_repo, gitea_pr_id FROM sessions WHERE id = ?", (session_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
    
    gitea_user, gitea_repo, gitea_pr_id = row
    
    if not gitea_pr_id:
        conn.close()
        raise HTTPException(status_code=404, detail="PR not created for this session")
    
    pr_data = gitea_client.get_pull_request(gitea_user, gitea_repo, gitea_pr_id)
    
    if not pr_data:
        conn.close()
        raise HTTPException(status_code=404, detail="PR not found in Gitea")
    
    # Получаем комментарии к PR
    pr_comments = gitea_client.get_pull_request_comments(gitea_user, gitea_repo, gitea_pr_id)
    issue_comments = gitea_client.get_pull_request_issue_comments(gitea_user, gitea_repo, gitea_pr_id)
    all_comments = pr_comments + issue_comments
    
    # Проверяем, есть ли сигнал готовности в комментариях (автоматически обновляем статус)
    ready_keywords = ["✅ ready", "ready", "готов", "готов к проверке", "готов к ревью", 
                      "готово", "завершено", "done", "completed", "✓ ready", "🎯 ready"]
    
    for comment in all_comments:
        body = comment.get("body", "").lower().strip()
        if any(keyword in body for keyword in ready_keywords):
            # Проверяем, не установлен ли уже candidate_ready_at
            c.execute("SELECT candidate_ready_at FROM sessions WHERE id = ?", (session_id,))
            current_ready_at = c.fetchone()[0]
            if not current_ready_at:
                # Устанавливаем candidate_ready_at
                created_at = comment.get("created_at")
                ready_at = created_at if created_at else datetime.utcnow().isoformat() + 'Z'
                c.execute("UPDATE sessions SET candidate_ready_at = ? WHERE id = ?", (ready_at, session_id))
                conn.commit()
                logger.info(f"Auto-detected candidate readiness from Gitea PR comment for session {session_id}")
            break
    
    # Получаем diff
    pr_diff = gitea_client.get_pull_request_diff(gitea_user, gitea_repo, gitea_pr_id)
    
    conn.close()
    
    return {
        "pr": pr_data,
        "comments": pr_comments,
        "issue_comments": issue_comments,
        "diff": pr_diff,
        "pr_url": f"{GITEA_WEB_URL}/{gitea_user}/{gitea_repo}/pulls/{gitea_pr_id}"
    }

# === API: Reviewer - Синхронизировать комментарии ИЗ Gitea PR в нашу систему ===
@app.post("/api/reviewer/sessions/{session_id}/gitea/sync-comments-from-gitea")
def reviewer_sync_comments_from_gitea(session_id: int):
    """
    Синхронизировать комментарии ИЗ Gitea PR в нашу систему (для отчёта)
    """
    if not gitea_client:
        raise HTTPException(status_code=503, detail="Gitea integration not available")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT comments, gitea_user, gitea_repo, gitea_pr_id FROM sessions WHERE id = ?", (session_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")
    
    comments_json, gitea_user, gitea_repo, gitea_pr_id = row
    existing_comments = json.loads(comments_json) if comments_json else []
    
    if not gitea_pr_id:
        conn.close()
        raise HTTPException(status_code=400, detail="PR not created for this session")
    
    # Получаем комментарии из Gitea PR (и review comments, и issue comments)
    logger.info(f"Syncing comments from Gitea PR {gitea_user}/{gitea_repo}#{gitea_pr_id} for session {session_id}")
    pr_comments = gitea_client.get_pull_request_comments(gitea_user, gitea_repo, gitea_pr_id)
    issue_comments = gitea_client.get_pull_request_issue_comments(gitea_user, gitea_repo, gitea_pr_id)
    
    logger.info(f"Retrieved {len(pr_comments)} review comments and {len(issue_comments)} issue comments from Gitea PR")
    
    # Объединяем все комментарии
    all_pr_comments = pr_comments + issue_comments
    
    if all_pr_comments:
        # Логируем структуру первого комментария для отладки
        logger.info(f"Sample comment structure: {json.dumps(all_pr_comments[0] if all_pr_comments else {}, indent=2)}")
    
    # Проверяем, есть ли сигнал готовности в комментариях
    ready_keywords = ["✅ ready", "ready", "готов", "готов к проверке", "готов к ревью", 
                      "готово", "завершено", "done", "completed", "✓ ready", "🎯 ready"]
    candidate_ready_detected = False
    ready_comment_time = None
    
    for comment in all_pr_comments:
        body = comment.get("body", "").lower().strip()
        # Проверяем, содержит ли комментарий сигнал готовности
        if any(keyword in body for keyword in ready_keywords):
            candidate_ready_detected = True
            # Получаем время создания комментария
            created_at = comment.get("created_at")
            if created_at:
                ready_comment_time = created_at
            break
    
    # Если обнаружен сигнал готовности и candidate_ready_at ещё не установлен
    if candidate_ready_detected:
        c.execute("SELECT candidate_ready_at FROM sessions WHERE id = ?", (session_id,))
        current_ready_at = c.fetchone()[0]
        if not current_ready_at:
            # Устанавливаем candidate_ready_at
            ready_at = ready_comment_time if ready_comment_time else datetime.utcnow().isoformat() + 'Z'
            c.execute("UPDATE sessions SET candidate_ready_at = ? WHERE id = ?", (ready_at, session_id))
            conn.commit()
            logger.info(f"Auto-detected candidate readiness from Gitea PR comment for session {session_id}")
    
    if not all_pr_comments:
        conn.close()
        return {
            "status": "ok",
            "synced_count": 0,
            "total_count": len(existing_comments),
            "message": "No comments found in Gitea PR",
            "candidate_ready_detected": candidate_ready_detected
        }
    
    # Конвертируем комментарии из Gitea в наш формат
    synced_count = 0
    existing_comment_ids = {c.get("gitea_id") for c in existing_comments if c.get("gitea_id")}
    
    # Пропускаем комментарии-сигналы готовности (они уже обработаны выше)
    for pr_comment in all_pr_comments:
        body = pr_comment.get("body", "").lower().strip()
        # Пропускаем комментарии-сигналы готовности (не добавляем их как code review комментарии)
        if any(keyword in body for keyword in ready_keywords):
            continue
        # Проверяем, не добавлен ли уже этот комментарий
        gitea_comment_id = pr_comment.get("id")
        if gitea_comment_id and gitea_comment_id in existing_comment_ids:
            continue
        
        # Парсим комментарий из Gitea
        # Формат Gitea: body может содержать [TYPE] SEVERITY\n\nтекст
        body = pr_comment.get("body", "")
        comment_type = "bug"
        severity = "medium"
        text = body
        
        # Пытаемся извлечь тип и серьёзность из формата [TYPE] SEVERITY
        lines = body.split("\n", 2)
        if len(lines) >= 2 and lines[0].startswith("[") and "]" in lines[0]:
            type_part = lines[0].split("]")[0].replace("[", "").strip().lower()
            severity_part = lines[0].split("]")[1].strip().lower() if "]" in lines[0] else "medium"
            text = "\n".join(lines[2:]) if len(lines) > 2 else body
            
            # Маппинг типов
            type_map = {"bug": "bug", "security": "security", "style": "style", "performance": "performance"}
            comment_type = type_map.get(type_part, "bug")
            
            # Маппинг серьёзности
            severity_map = {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}
            severity = severity_map.get(severity_part, "medium")
        
        # Извлекаем информацию о файле и строке
        # В Gitea комментарии могут иметь разные поля: path, original_path, diff_hunk, line, original_line
        path = pr_comment.get("path") or pr_comment.get("original_path") or "main.py"
        line = pr_comment.get("line") or pr_comment.get("original_line") or pr_comment.get("new_line") or 1
        line_range = f"{line}-{line}"
        
        logger.info(f"Parsing comment: path={path}, line={line}, gitea_id={gitea_comment_id}, body_preview={text[:50] if text else 'empty'}...")
        
        # Создаём комментарий в нашем формате
        new_comment = {
            "file": path,
            "line_range": line_range,
            "type": comment_type,
            "severity": severity,
            "text": text,
            "gitea_id": gitea_comment_id,  # Сохраняем ID для избежания дубликатов
            "source": "gitea"  # Помечаем, что комментарий из Gitea
        }
        
        existing_comments.append(new_comment)
        synced_count += 1
        logger.info(f"Added comment {synced_count}: file={path}, line={line}")
    
    # Сохраняем обновлённые комментарии
    c.execute("UPDATE sessions SET comments = ? WHERE id = ?", (json.dumps(existing_comments), session_id))
    conn.commit()
    conn.close()
    
    logger.info(f"Comment sync completed for session {session_id}: synced {synced_count} new comments, total {len(existing_comments)} comments")
    
    return {
        "status": "ok",
        "synced_count": synced_count,
        "total_count": len(existing_comments),
        "message": f"Synced {synced_count} comments from Gitea",
        "candidate_ready_detected": candidate_ready_detected
    }

# === API: Reviewer - Синхронизировать комментарии в Gitea PR ===
@app.post("/api/reviewer/sessions/{session_id}/gitea/sync-comments")
def reviewer_sync_gitea_comments(session_id: int):
    """
    Синхронизировать комментарии из нашей системы в Gitea PR
    """
    if not gitea_client:
        raise HTTPException(status_code=503, detail="Gitea integration not available")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT comments, gitea_user, gitea_repo, gitea_pr_id FROM sessions WHERE id = ?", (session_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    
    comments_json, gitea_user, gitea_repo, gitea_pr_id = row
    
    if not gitea_pr_id:
        raise HTTPException(status_code=400, detail="PR not created for this session")
    
    comments = json.loads(comments_json) if comments_json else []
    
    synced_count = 0
    errors = []
    
    for comment in comments:
        # Пропускаем комментарии, которые уже из Gitea (чтобы не дублировать)
        if comment.get("source") == "gitea" or comment.get("gitea_id"):
            continue
            
        try:
            # Парсим line_range для получения номера строки
            line = 1
            if comment.get("line_range"):
                # Пытаемся извлечь номер строки из line_range (например, "10-15" -> 10)
                try:
                    line = int(comment.get("line_range", "1").split("-")[0])
                except:
                    line = 1
            
            # Создаём комментарий в Gitea PR
            comment_body = f"[{comment.get('type', 'comment').upper()}] {comment.get('severity', 'medium').upper()}\n\n{comment.get('text', '')}"
            
            result = gitea_client.create_pull_request_comment(
                owner=gitea_user,
                repo=gitea_repo,
                pr_index=gitea_pr_id,
                body=comment_body,
                path=comment.get("file", "main.py"),
                line=line,
                side="RIGHT"
            )
            
            if result:
                synced_count += 1
        except Exception as e:
            errors.append(f"Failed to sync comment: {str(e)}")
    
    return {
        "status": "ok",
        "synced_count": synced_count,
        "total_count": len(comments),
        "errors": errors
    }

# === НОВОЕ: PDF ОТЧЁТ (старый endpoint для обратной совместимости) ===
@app.get("/api/sessions/{session_id}/report/pdf")
def get_pdf_report(session_id: int):
    session = get_session(session_id)
    diff_path = f"/artifacts/{session_id}_diff.patch"
    report_path = f"/artifacts/{session_id}_report.txt"

    diff_content = "# No diff"
    if os.path.exists(diff_path):
        with open(diff_path) as f:
            diff_content = f.read()

    report_content = "Отчёт ещё не готов..."
    if os.path.exists(report_path):
        with open(report_path) as f:
            report_content = f.read()

    # 2. HTML
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Code Review Report #{session_id}</title>
    <style>
        @page {{ size: A4; margin: 2cm; }}
        body {{ font-family: 'DejaVu Sans', sans-serif; line-height: 1.6; color: #333; }}
        h1, h2 {{ color: #2c3e50; }}
        .header {{ border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        pre {{ background: #f8f9fa; padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 12px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #f2f2f2; }}
        .critical {{ background: #ffebee; }}
        .high {{ background: #fff3e0; }}
        .medium {{ background: #fffde7; }}
        .low {{ background: #f3f4f7; }}
        .grade {{ font-size: 2em; font-weight: bold; text-align: center; margin: 20px 0; color: #27ae60; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Code Review Report</h1>
        <p><strong>Session ID:</strong> #{session['id']}</p>
        <p><strong>Candidate:</strong> {session['candidate_id']}</p>
        <p><strong>Date:</strong> {time.strftime("%d.%m.%Y %H:%M")}</p>
    </div>

    <div class="section">
        <h2>Evaluation Results</h2>
        <pre>{report_content}</pre>
        <div class="grade">
            {report_content.split('Grade: ')[-1].strip() if 'Grade:' in report_content else '—'}
        </div>
    </div>

    <div class="section">
        <h2>Comments ({len(session['comments'])})</h2>
        {"" if session['comments'] else "<p>No comments yet.</p>"}
        <table>
            <tr><th>File</th><th>Line</th><th>Type</th><th>Severity</th><th>Comment</th></tr>
            {''.join(
                f'<tr class="{c["severity"]}"><td>{c["file"]}</td><td>{c["line_range"]}</td><td>{c["type"]}</td><td>{c["severity"]}</td><td>{c["text"]}</td></tr>'
                for c in session['comments']
            )}
        </table>
    </div>

    <div class="section">
        <h2>Diff</h2>
        <pre>{diff_content}</pre>
    </div>
</body>
</html>"""

    # 3. Генерация PDF
    html = HTML(string=html_content)
    pdf_path = f"/artifacts/{session_id}_report.pdf"
    html.write_pdf(pdf_path)

    return FileResponse(pdf_path, media_type="application/pdf", filename=f"review_report_{session_id}.pdf")

# === API: Reviewer - Получить PDF отчёт ===
@app.get("/api/reviewer/sessions/{session_id}/report/pdf")
def reviewer_get_pdf_report(session_id: int):
    session = reviewer_get_session(session_id)
    diff_path = f"/artifacts/{session_id}_diff.patch"
    report_path = f"/artifacts/{session_id}_report.txt"

    diff_content = "# No diff"
    if os.path.exists(diff_path):
        with open(diff_path, encoding="utf-8") as f:
            diff_content = f.read()

    report_content = "Отчёт ещё не готов..."
    if os.path.exists(report_path):
        with open(report_path, encoding="utf-8") as f:
            report_content = f.read()

    # Статистика по комментариям
    comments = session.get('comments', [])
    comments_by_severity = {}
    comments_by_type = {}
    for c in comments:
        severity = c.get('severity', 'medium')
        comments_by_severity[severity] = comments_by_severity.get(severity, 0) + 1
        comment_type = c.get('type', 'comment')
        comments_by_type[comment_type] = comments_by_type.get(comment_type, 0) + 1

    # Форматирование дат
    def format_date(date_str):
        if not date_str:
            return "—"
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%d.%m.%Y %H:%M")
        except:
            return date_str

    created_at = format_date(session.get('created_at'))
    expires_at = format_date(session.get('expires_at'))
    candidate_ready_at = format_date(session.get('candidate_ready_at'))
    
    # Статус сессии
    status = session.get('status', 'active')
    status_text = {
        'active': 'Активна',
        'finished': 'Завершена',
        'expired': 'Истекла',
        'deleted': 'Удалена'
    }.get(status, status)

    # Gitea информация
    gitea_info = ""
    if session.get('gitea', {}).get('enabled'):
        gitea = session['gitea']
        gitea_info = f"""
        <div class="info-box" style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <h3 style="margin-top: 0; color: #1976d2;">Gitea Integration</h3>
            <p><strong>Пользователь:</strong> {gitea.get('user', '—')}</p>
            <p><strong>Репозиторий:</strong> {gitea.get('repo', '—')}</p>
            {f'<p><strong>Pull Request:</strong> PR #{gitea.get("pr_id", "—")}</p>' if gitea.get('pr_id') else ''}
            {f'<p><strong>Web URL:</strong> {gitea.get("web_url", "—")}</p>' if gitea.get('web_url') else ''}
        </div>
        """

    # Оценка из отчёта
    grade = "—"
    if 'Grade:' in report_content:
        grade = report_content.split('Grade:')[-1].strip().split('\n')[0].strip()
    elif 'Оценка:' in report_content:
        grade = report_content.split('Оценка:')[-1].strip().split('\n')[0].strip()

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Code Review Report #{session_id}</title>
    <style>
        @page {{ size: A4; margin: 2cm; }}
        body {{ font-family: 'DejaVu Sans', sans-serif; line-height: 1.6; color: #333; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        .header {{ border-bottom: 3px solid #3498db; padding-bottom: 15px; margin-bottom: 20px; }}
        .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }}
        .info-item {{ background: #f8f9fa; padding: 12px; border-radius: 6px; }}
        .info-item strong {{ display: block; color: #666; font-size: 0.9em; margin-bottom: 5px; }}
        .info-item span {{ font-size: 1.1em; color: #1a1a1a; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 20px 0; }}
        .stat-box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
        .stat-box .stat-value {{ font-size: 2em; font-weight: bold; color: #3498db; }}
        .stat-box .stat-label {{ color: #666; font-size: 0.9em; margin-top: 5px; }}
        pre {{ background: #f8f9fa; padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 11px; border: 1px solid #ddd; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 0.9em; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #3498db; color: white; font-weight: bold; }}
        .critical {{ background: #ffebee; }}
        .high {{ background: #fff3e0; }}
        .medium {{ background: #fffde7; }}
        .low {{ background: #f3f4f7; }}
        .grade-box {{ background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%); color: white; padding: 20px; border-radius: 12px; text-align: center; margin: 20px 0; }}
        .grade-box .grade-value {{ font-size: 3em; font-weight: bold; margin: 10px 0; }}
        .grade-box .grade-label {{ font-size: 1.2em; opacity: 0.9; }}
        .section {{ margin: 30px 0; page-break-inside: avoid; }}
        .status-badge {{ display: inline-block; padding: 6px 12px; border-radius: 20px; font-size: 0.9em; font-weight: bold; }}
        .status-active {{ background: #d4edda; color: #155724; }}
        .status-finished {{ background: #cce5ff; color: #004085; }}
        .status-expired {{ background: #f8d7da; color: #721c24; }}
        .status-deleted {{ background: #e2e3e5; color: #383d41; }}
    </style>
</head>
<body>
    <div class="header">
        <h1 style="margin-top: 0;">Code Review Report</h1>
        <div class="info-grid">
            <div class="info-item">
                <strong>ID Сессии</strong>
                <span>#{session['id']}</span>
            </div>
            <div class="info-item">
                <strong>Статус</strong>
                <span class="status-badge status-{status}">{status_text}</span>
            </div>
            <div class="info-item">
                <strong>Кандидат</strong>
                <span>{session['candidate_name']}</span>
            </div>
            <div class="info-item">
                <strong>Проверяющий</strong>
                <span>{session.get('reviewer_name', 'Не указан')}</span>
            </div>
            <div class="info-item">
                <strong>MR Package</strong>
                <span>{session.get('mr_package', '—')}</span>
            </div>
            <div class="info-item">
                <strong>Дата создания</strong>
                <span>{created_at}</span>
            </div>
            <div class="info-item">
                <strong>Истекает</strong>
                <span>{expires_at}</span>
            </div>
            {f'<div class="info-item"><strong>Готовность кандидата</strong><span>{candidate_ready_at}</span></div>' if candidate_ready_at and candidate_ready_at != "—" else ''}
        </div>
    </div>

    {gitea_info}

    <div class="section">
        <h2>Оценка</h2>
        <div class="grade-box">
            <div class="grade-label">Итоговая оценка</div>
            <div class="grade-value">{grade}</div>
        </div>
    </div>

    <div class="section">
        <h2>Статистика комментариев</h2>
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-value">{len(comments)}</div>
                <div class="stat-label">Всего комментариев</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{comments_by_severity.get('critical', 0)}</div>
                <div class="stat-label">Критичных</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{comments_by_severity.get('high', 0)}</div>
                <div class="stat-label">Высокий приоритет</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{comments_by_severity.get('medium', 0)}</div>
                <div class="stat-label">Средний приоритет</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Детальный отчёт</h2>
        <pre>{report_content}</pre>
    </div>

    <div class="section">
        <h2>Комментарии ({len(comments)})</h2>
        {"" if comments else "<p style='color: #999; font-style: italic;'>Комментариев пока нет</p>"}
        {('''
        <table>
            <tr>
                <th style="width: 20%;">Файл</th>
                <th style="width: 10%;">Строки</th>
                <th style="width: 15%;">Тип</th>
                <th style="width: 12%;">Приоритет</th>
                <th style="width: 43%;">Комментарий</th>
            </tr>
            ''' + ''.join(
                f'<tr class="{c.get("severity", "medium")}"><td>{c.get("file", "unknown")}</td><td>{c.get("line_range", "-")}</td><td>{c.get("type", "comment")}</td><td>{c.get("severity", "medium")}</td><td>{c.get("text", "").replace("<", "&lt;").replace(">", "&gt;")}</td></tr>'
                for c in comments
            ) + '''
        </table>
        ''') if comments else ""}
    </div>

    <div class="section">
        <h2>Diff</h2>
        <pre>{diff_content[:5000] if len(diff_content) > 5000 else diff_content}{"..." if len(diff_content) > 5000 else ""}</pre>
    </div>

    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 0.9em; text-align: center;">
        <p>Сгенерировано: {time.strftime("%d.%m.%Y %H:%M:%S")}</p>
        <p>Code Review Platform</p>
    </div>
</body>
</html>"""

    html = HTML(string=html_content)
    pdf_path = f"/artifacts/{session_id}_report.pdf"
    html.write_pdf(pdf_path)

    return FileResponse(pdf_path, media_type="application/pdf", filename=f"review_report_{session_id}.pdf")

# === API: Reviewer - Получить текстовый отчёт ===
@app.get("/api/reviewer/sessions/{session_id}/report")
def reviewer_get_report(session_id: int):
    report_path = f"/artifacts/{session_id}_report.txt"
    if not os.path.exists(report_path):
        from fastapi.responses import Response
        return Response(content="Отчёт ещё не готов...", media_type="text/plain; charset=utf-8")
    
    with open(report_path, "r", encoding="utf-8") as f:
        report_content = f.read()
    
    from fastapi.responses import Response
    return Response(content=report_content, media_type="text/plain; charset=utf-8")

# === SPA ===
# Catch-all роут должен быть последним, чтобы не перехватывать API запросы
# ВАЖНО: Этот роут регистрируется последним, но FastAPI всё равно может его вызвать
# если специфичные роуты не найдены. Поэтому мы явно проверяем и возвращаем 404
# для API запросов, которые не были обработаны выше.
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_spa(request: Request, full_path: str):
    # Не перехватываем API запросы - они должны обрабатываться роутерами выше
    # Проверяем без слеша в начале, т.к. full_path не содержит начальный слеш
    if full_path.startswith("api/"):
        # Если это API запрос, который не был обработан выше, значит роут не найден
        # Но сначала проверяем, может это просто не зарегистрированный роут
        raise HTTPException(status_code=404, detail=f"API endpoint not found: /{full_path}")
    if full_path.startswith("artifacts/") or full_path.startswith("assets/"):
        raise HTTPException(status_code=404, detail=f"Path not found: /{full_path}")

    file_path = os.path.join("static", full_path)
    if full_path and os.path.isfile(file_path):
        return FileResponse(file_path)

    return templates.TemplateResponse("index.html", {"request": request})
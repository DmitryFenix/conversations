# api/main.py
from fastapi import FastAPI, Request, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import sqlite3
import json
import os
import shutil
import zipfile
import logging
from rq import Queue
from redis import Redis
import time
from eval_worker import evaluate
from datetime import datetime, timedelta

# === PDF ===
from weasyprint import HTML


# === ЛОГИРОВАНИЕ ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === БД ===
DB_PATH = "/app/reviews.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
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

    conn.commit()
    conn.close()
init_db()

# === Redis + RQ ===
redis_conn = Redis(host='redis', port=6379)
queue = Queue(connection=redis_conn)

# === FastAPI ===
app = FastAPI()

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

# === Модели ===
class SessionCreate(BaseModel):
    candidate_id: str
    mr_package: str

# === API: Создать сессию ===
@app.post("/api/sessions")
def create_session(payload: SessionCreate):
    logger.info(f"Creating session for candidate_id={payload.candidate_id}, mr_package={payload.mr_package}")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    now = datetime.utcnow()
    expires_at = now + timedelta(hours=2)

    c.execute(
        "INSERT INTO sessions (candidate_id, mr_package, comments, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
        (payload.candidate_id, payload.mr_package, json.dumps([]), now.isoformat() + 'Z', expires_at.isoformat() + 'Z')
    )
    session_id = c.lastrowid
    conn.commit()
    conn.close()

    diff_path = f"/artifacts/{session_id}_diff.patch"
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
    with open(diff_path, "w") as f:
        f.write(demo_diff)

    return {"session_id": session_id}

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

    c.execute(
        "INSERT INTO sessions (candidate_id, mr_package, comments, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
        (f"upload_{int(time.time())}", file.filename, json.dumps([]), now.isoformat() + 'Z', expires_at.isoformat() + 'Z')
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

    return {"session_id": session_id}

# === API: Оценка ===
@app.get("/api/sessions/{session_id}/evaluate")
def evaluate_session(session_id: int):
    job = queue.enqueue("eval_worker.evaluate", session_id)
    return {"job_id": job.id}

@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    job = queue.fetch_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": job.get_status(), "result": job.result}

# === API: Добавить комментарий ===
@app.post("/api/sessions/{session_id}/comments")
def add_comment(session_id: int, comment: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT comments FROM sessions WHERE id = ?", (session_id,))
    row = c.fetchone()
    if not row:
        raise HTTPException(status_code=404)
    comments = json.loads(row[0])
    comments.append(comment)
    c.execute("UPDATE sessions SET comments = ? WHERE id = ?", (json.dumps(comments), session_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}

# === API: Продлить сессию на 30 минут ===
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
        if expires_str.endswith('Z'):
            expires_str = expires_str[:-1] + '+00:00'
        current_expires = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
        # Если нет timezone info, считаем UTC
        if current_expires.tzinfo is None:
            from datetime import timezone
            current_expires = current_expires.replace(tzinfo=timezone.utc)
        # Конвертируем в UTC naive для вычислений
        current_expires = current_expires.replace(tzinfo=None)
    else:
        current_expires = datetime.utcnow()
    
    # Продлеваем на 30 минут
    new_expires_at = current_expires + timedelta(minutes=30)
    
    c.execute("UPDATE sessions SET expires_at = ? WHERE id = ?", (new_expires_at.isoformat() + 'Z', session_id))
    conn.commit()
    conn.close()
    
    return {
        "status": "ok",
        "expires_at": new_expires_at.isoformat()
    }

# === НОВОЕ: PDF ОТЧЁТ ===
# === PDF ОТЧЁТ — ИСПРАВЛЕНО НА 100% ===
@app.get("/api/sessions/{session_id}/report/pdf")
def get_pdf_report(session_id: int):  # ← УБРАЛ async
    # 1. Получаем данные — БЕЗ AWAIT
    session = get_session(session_id)  # ← НЕ await!
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
# === SPA ===
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_spa(request: Request, full_path: str):
    if full_path.startswith("api/") or full_path.startswith("artifacts/") or full_path.startswith("assets/"):
        raise HTTPException(status_code=404)

    file_path = os.path.join("static", full_path)
    if full_path and os.path.isfile(file_path):
        return FileResponse(file_path)

    return templates.TemplateResponse("index.html", {"request": request})
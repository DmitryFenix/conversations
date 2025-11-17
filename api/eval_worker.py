# worker/eval_worker.py
import json
import os
import logging
import sqlite3
from redis import Redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def evaluate(session_id: int):
    logger.info(f"[Worker] Starting evaluation for session {session_id}")

    # Подключаемся к Redis (внутри функции — безопасно)
    try:
        redis_conn = Redis(host='redis', port=6379, decode_responses=True)
        redis_conn.ping()  # Проверка подключения
        logger.info("[Worker] Connected to Redis")
    except Exception as e:
        logger.error(f"[Worker] Cannot connect to Redis: {e}")
        return

    # 1. Читаем сессию
    # Используем тот же путь к БД, что и в main.py
    DB_PATH = "/app/reviews.db"
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT comments, mr_package FROM sessions WHERE id = ?", (session_id,))
        result = c.fetchone()
        conn.close()
        if not result:
            logger.error(f"[Worker] Session {session_id} not found in DB")
            return
        comments_json, mr_package = result
        comments = json.loads(comments_json) if comments_json else []
        logger.info(f"[Worker] Loaded session {session_id}, {len(comments)} comments, mr_package={mr_package}")
    except Exception as e:
        logger.error(f"[Worker] DB error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return

    # 2. golden_truth.json
    gt_path = f"/mr_packages/{mr_package}/golden_truth.json"
    logger.info(f"[Worker] Looking for golden_truth at: {gt_path}")
    if not os.path.exists(gt_path):
        logger.warning(f"[Worker] Golden truth not found: {gt_path}, using empty list")
        gt = []
    else:
        try:
            with open(gt_path, "r") as f:
                gt = json.load(f)
                logger.info(f"[Worker] Loaded {len(gt)} golden truth items")
        except Exception as e:
            logger.error(f"[Worker] Failed to read golden_truth: {e}")
            gt = []

    # 3. Оценка
    tp = []
    fp = []
    fn = gt.copy()

    for comment in comments:
        matched = False
        for defect in gt:
            if (comment["file"] == defect["file"] and
                comment["line_range"] == defect["line_range"] and
                comment["type"] == defect["type"]):
                tp.append(defect)
                if defect in fn:
                    fn.remove(defect)
                matched = True
                break
        if not matched:
            fp.append(comment)

    total = len(tp) + len(fp) + len(fn)
    score = len(tp) / total if total > 0 else 0
    grade = "Junior" if score < 0.45 else "Middle" if score < 0.70 else "Senior"
    
    # 4. Отчёт
    report_path = f"/artifacts/{session_id}_report.txt"
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"Evaluation Report for Session #{session_id}\n")
            f.write(f"{'='*50}\n\n")
            f.write(f"True Positives (TP): {len(tp)}\n")
            f.write(f"False Positives (FP): {len(fp)}\n")
            f.write(f"False Negatives (FN): {len(fn)}\n")
            f.write(f"Total: {total}\n\n")
            f.write(f"Score: {score:.3f}\n")
            f.write(f"Grade: {grade}\n")
        logger.info(f"[Worker] Report saved successfully: {report_path}")
    except Exception as e:
        logger.error(f"[Worker] Failed to save report: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return

    logger.info(f"[Worker] Evaluation complete: score={score:.3f}, grade={grade}, TP={len(tp)}, FP={len(fp)}, FN={len(fn)}")
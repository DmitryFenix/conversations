"""
Простой dashboard для мониторинга RQ задач
Можно добавить как endpoint в FastAPI
"""
from fastapi import APIRouter, HTTPException
from rq_monitor import RQMonitor
from redis import Redis
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rq", tags=["RQ Monitoring"])


def get_redis_connection():
    """Получить подключение к Redis (копия из main.py для избежания циклических импортов)"""
    from redis import Redis
    import time
    
    max_retries = 5
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            # Используем decode_responses=False для избежания проблем с UTF-8
            # RQ сам обработает декодирование
            conn = Redis(host='redis', port=6379, socket_connect_timeout=2, decode_responses=False)
            conn.ping()
            return conn
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}, retrying...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to Redis after {max_retries} attempts: {e}")
                raise


@router.get("/stats")
def get_rq_stats():
    """Получить статистику RQ очереди"""
    try:
        redis_conn = get_redis_connection()
        monitor = RQMonitor(redis_conn, "default")
        stats = monitor.get_queue_stats()
        return {
            "status": "ok",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get RQ stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/recent")
def get_recent_jobs(limit: int = 10):
    """Получить список недавних задач"""
    try:
        redis_conn = get_redis_connection()
        monitor = RQMonitor(redis_conn, "default")
        jobs = monitor.get_recent_jobs(limit)
        return {
            "status": "ok",
            "jobs": jobs,
            "count": len(jobs)
        }
    except Exception as e:
        logger.error(f"Failed to get recent jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
def get_job_details(job_id: str):
    """Получить детальную информацию о задаче"""
    try:
        redis_conn = get_redis_connection()
        monitor = RQMonitor(redis_conn, "default")
        job_info = monitor.get_job_info(job_id)
        
        if not job_info:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "status": "ok",
            "job": job_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
def get_performance_metrics(hours: int = 24):
    """
    Получить метрики производительности за последние N часов
    
    Args:
        hours: Количество часов для анализа (по умолчанию 24)
    """
    try:
        redis_conn = get_redis_connection()
        monitor = RQMonitor(redis_conn, "default")
        metrics = monitor.get_performance_metrics(hours=hours)
        return {
            "status": "ok",
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/trends")
def get_performance_trends(periods: int = 6, hours_per_period: int = 4):
    """
    Получить тренды производительности за несколько периодов
    
    Args:
        periods: Количество периодов для анализа (по умолчанию 6)
        hours_per_period: Количество часов в каждом периоде (по умолчанию 4)
    """
    try:
        redis_conn = get_redis_connection()
        monitor = RQMonitor(redis_conn, "default")
        trends = monitor.get_performance_trends(periods=periods, hours_per_period=hours_per_period)
        return {
            "status": "ok",
            "trends": trends
        }
    except Exception as e:
        logger.error(f"Failed to get performance trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/compare")
def get_efficiency_comparison(current_hours: int = 1, previous_hours: int = 1):
    """
    Сравнить эффективность текущего периода с предыдущим
    
    Args:
        current_hours: Количество часов для текущего периода (по умолчанию 1)
        previous_hours: Количество часов для предыдущего периода (по умолчанию 1)
    """
    try:
        redis_conn = get_redis_connection()
        monitor = RQMonitor(redis_conn, "default")
        comparison = monitor.get_efficiency_comparison(
            current_hours=current_hours,
            previous_hours=previous_hours
        )
        return {
            "status": "ok",
            "comparison": comparison
        }
    except Exception as e:
        logger.error(f"Failed to get efficiency comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))


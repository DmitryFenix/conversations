"""
Мониторинг и оптимизация RQ задач
"""
import logging
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from rq import Queue
from rq.job import Job
from redis import Redis
from collections import defaultdict

logger = logging.getLogger(__name__)


class RQMonitor:
    """Класс для мониторинга RQ задач"""
    
    def __init__(self, redis_conn: Redis, queue_name: str = "default"):
        self.redis_conn = redis_conn
        self.queue = Queue(queue_name, connection=redis_conn)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Получить статистику очереди"""
        return {
            "queue_name": self.queue.name,
            "queued": len(self.queue),
            "started": len(self.queue.started_job_registry),
            "finished": len(self.queue.finished_job_registry),
            "failed": len(self.queue.failed_job_registry),
            "deferred": len(self.queue.deferred_job_registry),
            "scheduled": len(self.queue.scheduled_job_registry),
        }
    
    def get_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Получить детальную информацию о задаче"""
        try:
            job = Job.fetch(job_id, connection=self.redis_conn)
            
            # Безопасное преобразование result и exc_info в строки
            result_str = None
            if job.result is not None:
                try:
                    result_str = str(job.result)
                except (UnicodeDecodeError, AttributeError):
                    result_str = repr(job.result)
            
            exc_info_str = None
            if job.exc_info is not None:
                try:
                    exc_info_str = str(job.exc_info)
                except (UnicodeDecodeError, AttributeError):
                    exc_info_str = repr(job.exc_info)
            
            info = {
                "id": job.id,
                "status": job.get_status(),
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                "result": result_str,
                "exc_info": exc_info_str,
                "timeout": job.timeout,
                "retry": job.retries_left if hasattr(job, 'retries_left') else None,
            }
            
            # Вычисляем время выполнения
            if job.started_at and job.ended_at:
                info["duration"] = (job.ended_at - job.started_at).total_seconds()
            elif job.started_at:
                now = datetime.now(timezone.utc) if job.started_at.tzinfo else datetime.utcnow()
                started = job.started_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                info["duration"] = (now - started).total_seconds()
            else:
                info["duration"] = None
            
            return info
        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode job data for {job_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get job info for {job_id}: {e}")
            return None
    
    def get_recent_jobs(self, limit: int = 10) -> list:
        """Получить список недавних задач"""
        jobs = []
        try:
            # Получаем задачи из разных регистров
            all_job_ids = (
                list(self.queue.job_ids) +
                list(self.queue.started_job_registry.get_job_ids()) +
                list(self.queue.finished_job_registry.get_job_ids()[:limit]) +
                list(self.queue.failed_job_registry.get_job_ids()[:limit])
            )
            
            # Убираем дубликаты и ограничиваем
            unique_job_ids = list(set(all_job_ids))[:limit]
            
            for job_id in unique_job_ids:
                job_info = self.get_job_info(job_id)
                if job_info:
                    jobs.append(job_info)
            
            # Сортируем по времени создания (новые первыми)
            jobs.sort(key=lambda x: x.get("created_at") or "", reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get recent jobs: {e}")
        
        return jobs
    
    def log_queue_stats(self):
        """Логировать статистику очереди"""
        stats = self.get_queue_stats()
        logger.info(f"RQ Queue Stats: {stats}")
    
    def log_job_enqueued(self, job: Job, session_id: int):
        """Логировать постановку задачи в очередь"""
        logger.info(
            f"Job enqueued: id={job.id}, session_id={session_id}, "
            f"queue={self.queue.name}, timeout={job.timeout}"
        )
    
    def log_job_started(self, job_id: str):
        """Логировать начало выполнения задачи"""
        job_info = self.get_job_info(job_id)
        if job_info:
            created_at_str = job_info.get('created_at')
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    queued_for = (now - created_at).total_seconds()
                    logger.info(f"Job started: id={job_id}, queued_for={queued_for:.2f}s")
                except Exception:
                    logger.info(f"Job started: id={job_id}")
            else:
                logger.info(f"Job started: id={job_id}")
    
    def log_job_finished(self, job_id: str, result: Any = None):
        """Логировать завершение задачи"""
        job_info = self.get_job_info(job_id)
        if job_info:
            duration = job_info.get("duration")
            logger.info(
                f"Job finished: id={job_id}, "
                f"duration={duration:.2f}s" if duration else f"status={job_info.get('status')}"
            )
    
    def log_job_failed(self, job_id: str, error: Exception = None):
        """Логировать ошибку задачи"""
        job_info = self.get_job_info(job_id)
        error_msg = str(error) if error else job_info.get("exc_info") if job_info else "Unknown error"
        logger.error(
            f"Job failed: id={job_id}, error={error_msg}"
        )
    
    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Получить метрики производительности за последние N часов
        
        Args:
            hours: Количество часов для анализа (по умолчанию 24)
        
        Returns:
            Словарь с метриками производительности
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Получаем все завершённые задачи
            finished_jobs = []
            for job_id in self.queue.finished_job_registry.get_job_ids():
                try:
                    job_info = self.get_job_info(job_id)
                    if job_info:
                        created_at_str = job_info.get("created_at")
                        if created_at_str:
                            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            if created_at >= cutoff_time:
                                finished_jobs.append(job_info)
                except Exception as e:
                    logger.debug(f"Failed to process job {job_id}: {e}")
                    continue
            
            # Получаем все неудачные задачи
            failed_jobs = []
            for job_id in self.queue.failed_job_registry.get_job_ids():
                try:
                    job_info = self.get_job_info(job_id)
                    if job_info:
                        created_at_str = job_info.get("created_at")
                        if created_at_str:
                            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            if created_at >= cutoff_time:
                                failed_jobs.append(job_info)
                except Exception as e:
                    logger.debug(f"Failed to process failed job {job_id}: {e}")
                    continue
            
            total_jobs = len(finished_jobs) + len(failed_jobs)
            successful_jobs = len(finished_jobs)
            failed_count = len(failed_jobs)
            
            # Вычисляем метрики времени выполнения
            durations = [j.get("duration") for j in finished_jobs if j.get("duration") is not None]
            
            avg_duration = sum(durations) / len(durations) if durations else 0
            median_duration = sorted(durations)[len(durations) // 2] if durations else 0
            min_duration = min(durations) if durations else 0
            max_duration = max(durations) if durations else 0
            
            # Вычисляем время ожидания в очереди
            queue_times = []
            for job in finished_jobs + failed_jobs:
                created_at_str = job.get("created_at")
                started_at_str = job.get("started_at")
                if created_at_str and started_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        started_at = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
                        queue_time = (started_at - created_at).total_seconds()
                        if queue_time >= 0:
                            queue_times.append(queue_time)
                    except Exception:
                        pass
            
            avg_queue_time = sum(queue_times) / len(queue_times) if queue_times else 0
            max_queue_time = max(queue_times) if queue_times else 0
            
            # Вычисляем пропускную способность (задач в час)
            if total_jobs > 0:
                throughput = total_jobs / hours
            else:
                throughput = 0
            
            # Процент успешных задач
            success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0
            
            return {
                "period_hours": hours,
                "total_jobs": total_jobs,
                "successful_jobs": successful_jobs,
                "failed_jobs": failed_count,
                "success_rate": round(success_rate, 2),
                "throughput_per_hour": round(throughput, 2),
                "duration_metrics": {
                    "avg_seconds": round(avg_duration, 2),
                    "median_seconds": round(median_duration, 2),
                    "min_seconds": round(min_duration, 2),
                    "max_seconds": round(max_duration, 2),
                },
                "queue_time_metrics": {
                    "avg_seconds": round(avg_queue_time, 2),
                    "max_seconds": round(max_queue_time, 2),
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {
                "error": str(e),
                "period_hours": hours,
                "total_jobs": 0,
            }
    
    def get_performance_trends(self, periods: int = 6, hours_per_period: int = 4) -> Dict[str, Any]:
        """
        Получить тренды производительности за несколько периодов
        
        Args:
            periods: Количество периодов для анализа
            hours_per_period: Количество часов в каждом периоде
        
        Returns:
            Словарь с трендами по периодам
        """
        trends = []
        for i in range(periods):
            hours_start = (i + 1) * hours_per_period
            hours_end = i * hours_per_period
            period_metrics = self.get_performance_metrics(hours=hours_start)
            
            # Вычисляем метрики только для текущего периода (вычитаем предыдущий)
            if i > 0:
                prev_metrics = self.get_performance_metrics(hours=hours_end)
                period_metrics = {
                    "period": i + 1,
                    "hours_range": f"{hours_end}-{hours_start}",
                    "total_jobs": period_metrics.get("total_jobs", 0) - prev_metrics.get("total_jobs", 0),
                    "successful_jobs": period_metrics.get("successful_jobs", 0) - prev_metrics.get("successful_jobs", 0),
                    "failed_jobs": period_metrics.get("failed_jobs", 0) - prev_metrics.get("failed_jobs", 0),
                    "success_rate": period_metrics.get("success_rate", 0),
                    "avg_duration": period_metrics.get("duration_metrics", {}).get("avg_seconds", 0),
                    "throughput": period_metrics.get("throughput_per_hour", 0),
                }
            else:
                period_metrics["period"] = i + 1
                period_metrics["hours_range"] = f"0-{hours_start}"
                period_metrics["avg_duration"] = period_metrics.get("duration_metrics", {}).get("avg_seconds", 0)
                period_metrics["throughput"] = period_metrics.get("throughput_per_hour", 0)
            
            trends.append(period_metrics)
        
        # Вычисляем изменения (тренды)
        if len(trends) >= 2:
            latest = trends[0]
            previous = trends[1]
            
            duration_change = latest.get("avg_duration", 0) - previous.get("avg_duration", 0)
            throughput_change = latest.get("throughput", 0) - previous.get("throughput", 0)
            success_rate_change = latest.get("success_rate", 0) - previous.get("success_rate", 0)
            
            return {
                "periods": trends,
                "trends": {
                    "duration_change_percent": round((duration_change / previous.get("avg_duration", 1)) * 100, 2) if previous.get("avg_duration", 0) > 0 else 0,
                    "throughput_change_percent": round((throughput_change / previous.get("throughput", 1)) * 100, 2) if previous.get("throughput", 0) > 0 else 0,
                    "success_rate_change": round(success_rate_change, 2),
                    "is_improving": duration_change < 0 and success_rate_change >= 0,
                },
                "summary": {
                    "latest_avg_duration": latest.get("avg_duration", 0),
                    "latest_throughput": latest.get("throughput", 0),
                    "latest_success_rate": latest.get("success_rate", 0),
                }
            }
        
        return {
            "periods": trends,
            "trends": None,
            "summary": trends[0] if trends else {}
        }
    
    def get_efficiency_comparison(self, current_hours: int = 1, previous_hours: int = 1) -> Dict[str, Any]:
        """
        Сравнить эффективность текущего периода с предыдущим
        
        Args:
            current_hours: Количество часов для текущего периода
            previous_hours: Количество часов для предыдущего периода (начинается после current_hours)
        
        Returns:
            Словарь с сравнением метрик
        """
        current_metrics = self.get_performance_metrics(hours=current_hours)
        previous_metrics = self.get_performance_metrics(hours=current_hours + previous_hours)
        
        # Вычисляем метрики только для предыдущего периода
        prev_total = previous_metrics.get("total_jobs", 0) - current_metrics.get("total_jobs", 0)
        prev_successful = previous_metrics.get("successful_jobs", 0) - current_metrics.get("successful_jobs", 0)
        prev_failed = previous_metrics.get("failed_jobs", 0) - current_metrics.get("failed_jobs", 0)
        
        prev_success_rate = (prev_successful / prev_total * 100) if prev_total > 0 else 0
        prev_avg_duration = previous_metrics.get("duration_metrics", {}).get("avg_seconds", 0)
        prev_throughput = prev_total / previous_hours if previous_hours > 0 else 0
        
        curr_avg_duration = current_metrics.get("duration_metrics", {}).get("avg_seconds", 0)
        curr_throughput = current_metrics.get("throughput_per_hour", 0)
        curr_success_rate = current_metrics.get("success_rate", 0)
        
        # Вычисляем изменения
        duration_change = curr_avg_duration - prev_avg_duration
        duration_change_percent = (duration_change / prev_avg_duration * 100) if prev_avg_duration > 0 else 0
        
        throughput_change = curr_throughput - prev_throughput
        throughput_change_percent = (throughput_change / prev_throughput * 100) if prev_throughput > 0 else 0
        
        success_rate_change = curr_success_rate - prev_success_rate
        
        return {
            "current_period": {
                "hours": current_hours,
                "total_jobs": current_metrics.get("total_jobs", 0),
                "successful_jobs": current_metrics.get("successful_jobs", 0),
                "failed_jobs": current_metrics.get("failed_jobs", 0),
                "success_rate": round(curr_success_rate, 2),
                "avg_duration_seconds": round(curr_avg_duration, 2),
                "throughput_per_hour": round(curr_throughput, 2),
            },
            "previous_period": {
                "hours": previous_hours,
                "total_jobs": prev_total,
                "successful_jobs": prev_successful,
                "failed_jobs": prev_failed,
                "success_rate": round(prev_success_rate, 2),
                "avg_duration_seconds": round(prev_avg_duration, 2),
                "throughput_per_hour": round(prev_throughput, 2),
            },
            "changes": {
                "duration_change_seconds": round(duration_change, 2),
                "duration_change_percent": round(duration_change_percent, 2),
                "throughput_change": round(throughput_change, 2),
                "throughput_change_percent": round(throughput_change_percent, 2),
                "success_rate_change": round(success_rate_change, 2),
                "is_improving": duration_change < 0 and success_rate_change >= 0,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class OptimizedQueue:
    """Оптимизированная очередь с приоритетами и retry"""
    
    def __init__(self, redis_conn: Redis, queue_name: str = "default"):
        self.redis_conn = redis_conn
        self.queue = Queue(queue_name, connection=redis_conn)
        self.monitor = RQMonitor(redis_conn, queue_name)
    
    def enqueue_evaluation(
        self,
        session_id: int,
        timeout: int = 300,  # 5 минут по умолчанию
        retry: int = 2,  # 2 попытки
        priority: str = "normal"  # normal, high, low
    ) -> Job:
        """
        Поставить задачу оценки в очередь с оптимизацией
        
        Args:
            session_id: ID сессии для оценки
            timeout: Таймаут выполнения в секундах
            retry: Количество повторных попыток
            priority: Приоритет задачи (normal, high, low)
        """
        # Определяем таймаут в зависимости от приоритета
        # Используем встроенную функцию max/min явно через builtins для избежания конфликтов
        import builtins as _builtins
        if priority == "high":
            timeout = _builtins.min(timeout, 600)  # Максимум 10 минут для высокого приоритета
        elif priority == "low":
            timeout = _builtins.max(timeout, 180)  # Минимум 3 минуты для низкого приоритета
        
        # В RQ 2.6.0 retry передается как число напрямую
        # Создаём задачу с параметрами
        # Примечание: в RQ 2.6.0 параметр retry может не поддерживаться напрямую
        # Используем только поддерживаемые параметры
        enqueue_kwargs = {
            "job_timeout": timeout,
            "result_ttl": 3600,  # Результат хранится 1 час
            "failure_ttl": 86400,  # Ошибки хранятся 24 часа
        }
        
        # Пробуем добавить retry если поддерживается
        # В RQ 2.6.0 retry может быть числом или объектом Retry
        try:
            from rq.retry import Retry
            enqueue_kwargs["retry"] = Retry(max=retry) if isinstance(retry, int) else retry
        except ImportError:
            # Если модуль не найден, пробуем передать как число
            # В некоторых версиях RQ retry может быть просто числом
            try:
                enqueue_kwargs["retry"] = retry
            except Exception:
                # Если не поддерживается, просто не передаем
                logger.warning(f"Retry parameter not supported in this RQ version, skipping")
        
        job = self.queue.enqueue(
            "eval_worker.evaluate",
            session_id,
            **enqueue_kwargs
        )
        
        # Логируем
        self.monitor.log_job_enqueued(job, session_id)
        
        return job
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику очереди"""
        return self.monitor.get_queue_stats()
    
    def get_recent_jobs(self, limit: int = 10) -> list:
        """Получить список недавних задач"""
        return self.monitor.get_recent_jobs(limit)


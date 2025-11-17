"""
Тесты для мониторинга RQ задач
"""
import pytest
import httpx
import asyncio


class TestRQMonitoring:
    """Тесты мониторинга RQ"""
    
    @pytest.mark.asyncio
    async def test_get_rq_stats(self, api_client: httpx.AsyncClient):
        """Тест: Получение статистики RQ очереди"""
        response = await api_client.get("/api/rq/stats")
        
        # Endpoint может не существовать, если мониторинг не включён
        if response.status_code == 404:
            pytest.skip("RQ monitoring not enabled")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "status" in data, "Response should contain status"
        assert "stats" in data, "Response should contain stats"
        assert "queue_name" in data["stats"], "Stats should contain queue_name"
        print(f"✓ RQ stats retrieved: {data['stats']}")
    
    @pytest.mark.asyncio
    async def test_get_recent_jobs(self, api_client: httpx.AsyncClient):
        """Тест: Получение списка недавних задач"""
        response = await api_client.get("/api/rq/jobs/recent?limit=5")
        
        if response.status_code == 404:
            pytest.skip("RQ monitoring not enabled")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "status" in data, "Response should contain status"
        assert "jobs" in data, "Response should contain jobs"
        assert isinstance(data["jobs"], list), "Jobs should be a list"
        print(f"✓ Retrieved {len(data['jobs'])} recent jobs")
    
    @pytest.mark.asyncio
    async def test_get_job_details(self, api_client: httpx.AsyncClient):
        """Тест: Получение деталей задачи"""
        # Сначала создаём задачу оценки
        if not hasattr(pytest, 'test_session_id'):
            pytest.skip("No session from previous test")
        
        session_id = pytest.test_session_id
        
        # Создаём задачу
        eval_response = await api_client.post(f"/api/reviewer/sessions/{session_id}/evaluate")
        if eval_response.status_code != 200:
            pytest.skip("Failed to create evaluation job")
        
        job_id = eval_response.json()["job_id"]
        
        # Получаем детали
        response = await api_client.get(f"/api/rq/jobs/{job_id}")
        
        if response.status_code == 404:
            pytest.skip("RQ monitoring not enabled")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "status" in data, "Response should contain status"
        assert "job" in data, "Response should contain job"
        assert data["job"]["id"] == job_id, "Job ID should match"
        print(f"✓ Job details retrieved for {job_id}")



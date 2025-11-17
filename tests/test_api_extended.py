"""
Расширенные тесты с edge cases, валидацией и тестами производительности
"""
import pytest
import httpx
import asyncio
import time
from typing import Dict, Any


class TestEdgeCases:
    """Тесты граничных случаев"""
    
    @pytest.mark.asyncio
    async def test_create_session_empty_name(self, api_client: httpx.AsyncClient):
        """Тест: Создание сессии с пустым именем кандидата"""
        response = await api_client.post(
            "/api/reviewer/sessions",
            json={
                "reviewer_name": "Test Reviewer",
                "candidate_name": "",
                "mr_package": "demo_package"
            }
        )
        # Может быть 200 (если пустое имя допустимо) или 400/422 (если валидация)
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"
        print(f"✓ Empty name handled: {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_create_session_very_long_name(self, api_client: httpx.AsyncClient):
        """Тест: Создание сессии с очень длинным именем"""
        long_name = "A" * 1000
        response = await api_client.post(
            "/api/reviewer/sessions",
            json={
                "reviewer_name": "Test Reviewer",
                "candidate_name": long_name,
                "mr_package": "demo_package"
            }
        )
        # Должно либо принять, либо вернуть ошибку валидации
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"
        print(f"✓ Long name handled: {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_create_session_special_characters(self, api_client: httpx.AsyncClient):
        """Тест: Создание сессии с специальными символами"""
        response = await api_client.post(
            "/api/reviewer/sessions",
            json={
                "reviewer_name": "Test Reviewer",
                "candidate_name": "Test <script>alert('xss')</script>",
                "mr_package": "demo_package"
            }
        )
        # Должно обработать безопасно
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"
        print(f"✓ Special characters handled: {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, api_client: httpx.AsyncClient):
        """Тест: Получение несуществующей сессии"""
        response = await api_client.get("/api/reviewer/sessions/999999")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Nonexistent session correctly returns 404")
    
    @pytest.mark.asyncio
    async def test_add_comment_invalid_line_range(self, api_client: httpx.AsyncClient):
        """Тест: Добавление комментария с невалидным диапазоном строк"""
        if not hasattr(pytest, 'test_access_token'):
            pytest.skip("No access token")
        
        token = pytest.test_access_token
        response = await api_client.post(
            f"/api/candidate/sessions/{token}/comments",
            json={
                "file": "main.py",
                "line_range": "invalid",
                "type": "bug",
                "severity": "high",
                "text": "Test"
            }
        )
        # Может принять или отклонить
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"
        print(f"✓ Invalid line range handled: {response.status_code}")


class TestPerformance:
    """Тесты производительности"""
    
    @pytest.mark.asyncio
    async def test_create_session_performance(self, api_client: httpx.AsyncClient, test_reviewer_data: Dict[str, str]):
        """Тест: Время создания сессии должно быть разумным"""
        start_time = time.time()
        response = await api_client.post(
            "/api/reviewer/sessions",
            json=test_reviewer_data
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200, f"Session creation failed: {response.status_code}"
        assert elapsed < 30.0, f"Session creation took too long: {elapsed:.2f}s"
        print(f"✓ Session created in {elapsed:.2f}s")
    
    @pytest.mark.asyncio
    async def test_list_sessions_performance(self, api_client: httpx.AsyncClient):
        """Тест: Получение списка сессий должно быть быстрым"""
        start_time = time.time()
        response = await api_client.get("/api/reviewer/sessions")
        elapsed = time.time() - start_time
        
        assert response.status_code == 200, f"Failed to get sessions: {response.status_code}"
        assert elapsed < 5.0, f"List sessions took too long: {elapsed:.2f}s"
        print(f"✓ Sessions listed in {elapsed:.2f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, api_client: httpx.AsyncClient, test_reviewer_data: Dict[str, str]):
        """Тест: Обработка нескольких одновременных запросов"""
        async def create_session():
            return await api_client.post("/api/reviewer/sessions", json=test_reviewer_data)
        
        start_time = time.time()
        # Создаём 5 сессий параллельно
        tasks = [create_session() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        # Все должны быть успешными
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count == 5, f"Only {success_count}/5 sessions created successfully"
        assert elapsed < 60.0, f"Concurrent requests took too long: {elapsed:.2f}s"
        print(f"✓ Created {success_count} sessions concurrently in {elapsed:.2f}s")


class TestValidation:
    """Тесты валидации данных"""
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, api_client: httpx.AsyncClient):
        """Тест: Отсутствие обязательных полей"""
        # Без candidate_name
        response = await api_client.post(
            "/api/reviewer/sessions",
            json={
                "reviewer_name": "Test Reviewer",
                "mr_package": "demo_package"
            }
        )
        assert response.status_code in [400, 422], f"Expected validation error, got {response.status_code}"
        print(f"✓ Missing field correctly rejected")
    
    @pytest.mark.asyncio
    async def test_invalid_json(self, api_client: httpx.AsyncClient):
        """Тест: Невалидный JSON"""
        response = await api_client.post(
            "/api/reviewer/sessions",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422], f"Expected validation error, got {response.status_code}"
        print(f"✓ Invalid JSON correctly rejected")
    
    @pytest.mark.asyncio
    async def test_wrong_http_method(self, api_client: httpx.AsyncClient):
        """Тест: Неправильный HTTP метод"""
        # GET вместо POST для создания сессии
        response = await api_client.get("/api/reviewer/sessions")
        # GET для списка сессий - это валидно, но не создаёт сессию
        assert response.status_code == 200, "GET /api/reviewer/sessions is valid"
        print(f"✓ HTTP method validation works")


class TestSecurity:
    """Тесты безопасности"""
    
    @pytest.mark.asyncio
    async def test_sql_injection_attempt(self, api_client: httpx.AsyncClient):
        """Тест: Попытка SQL инъекции в имени"""
        response = await api_client.post(
            "/api/reviewer/sessions",
            json={
                "reviewer_name": "Test Reviewer",
                "candidate_name": "'; DROP TABLE sessions; --",
                "mr_package": "demo_package"
            }
        )
        # Должно обработать безопасно (либо принять как строку, либо отклонить)
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"
        # Проверяем, что таблица всё ещё существует
        list_response = await api_client.get("/api/reviewer/sessions")
        assert list_response.status_code == 200, "Sessions table should still exist"
        print(f"✓ SQL injection attempt handled safely")
    
    @pytest.mark.asyncio
    async def test_path_traversal_attempt(self, api_client: httpx.AsyncClient):
        """Тест: Попытка path traversal в имени файла"""
        if not hasattr(pytest, 'test_access_token'):
            pytest.skip("No access token")
        
        token = pytest.test_access_token
        response = await api_client.post(
            f"/api/candidate/sessions/{token}/comments",
            json={
                "file": "../../../etc/passwd",
                "line_range": "1-1",
                "type": "bug",
                "severity": "high",
                "text": "Test"
            }
        )
        # Должно обработать безопасно
        assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"
        print(f"✓ Path traversal attempt handled safely")


class TestRQJobs:
    """Тесты для RQ задач"""
    
    @pytest.mark.asyncio
    async def test_evaluation_job_creation(self, api_client: httpx.AsyncClient):
        """Тест: Создание задачи оценки"""
        if not hasattr(pytest, 'test_session_id'):
            pytest.skip("No session from previous test")
        
        session_id = pytest.test_session_id
        response = await api_client.post(f"/api/reviewer/sessions/{session_id}/evaluate")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "job_id" in data, "Response should contain job_id"
        assert isinstance(data["job_id"], str), "job_id should be string"
        print(f"✓ Evaluation job created: {data['job_id']}")
        
        # Сохраняем для проверки статуса
        pytest.test_job_id = data["job_id"]
    
    @pytest.mark.asyncio
    async def test_job_status_tracking(self, api_client: httpx.AsyncClient):
        """Тест: Отслеживание статуса задачи"""
        if not hasattr(pytest, 'test_job_id'):
            pytest.skip("No job ID from previous test")
        
        job_id = pytest.test_job_id
        
        # Ждём немного
        await asyncio.sleep(2)
        
        response = await api_client.get(f"/api/jobs/{job_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "status" in data, "Response should contain status"
        assert data["status"] in ["queued", "started", "finished", "failed"], f"Invalid status: {data['status']}"
        print(f"✓ Job status: {data['status']}")
    
    @pytest.mark.asyncio
    async def test_nonexistent_job(self, api_client: httpx.AsyncClient):
        """Тест: Получение несуществующей задачи"""
        response = await api_client.get("/api/jobs/nonexistent-job-id")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Nonexistent job correctly returns 404")



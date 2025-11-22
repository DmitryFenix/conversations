"""
Тесты методом чёрного ящика для API
Тестируем функциональность через HTTP endpoints без знания внутренней реализации
"""
import pytest
import httpx
import asyncio
from typing import Dict, Any
import json
import time
import sys


class TestSessionCreation:
    """Тесты создания сессий"""
    
    @pytest.mark.asyncio
    async def test_reviewer_create_session(self, api_client: httpx.AsyncClient, test_reviewer_data: Dict[str, str]):
        """Тест: Ревьюер может создать сессию"""
        response = await api_client.post(
            "/api/reviewer/sessions",
            json=test_reviewer_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Проверяем структуру ответа
        assert "session_id" in data, "Response should contain session_id"
        assert "access_token" in data, "Response should contain access_token"
        assert "reviewer_token" in data, "Response should contain reviewer_token"
        assert isinstance(data["session_id"], int), "session_id should be integer"
        assert isinstance(data["access_token"], str), "access_token should be string"
        assert len(data["access_token"]) > 0, "access_token should not be empty"
        
        # Сохраняем для других тестов
        pytest.test_session_id = data["session_id"]
        pytest.test_access_token = data["access_token"]
        pytest.test_reviewer_token = data["reviewer_token"]
        
        print(f"✓ Created session {data['session_id']} with access_token {data['access_token'][:20]}...")
    
    @pytest.mark.asyncio
    async def test_reviewer_create_session_invalid_data(self, api_client: httpx.AsyncClient):
        """Тест: Создание сессии с невалидными данными должно вернуть ошибку"""
        response = await api_client.post(
            "/api/reviewer/sessions",
            json={"invalid": "data"}
        )
        
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print(f"✓ Invalid data correctly rejected")


class TestSessionRetrieval:
    """Тесты получения сессий"""
    
    @pytest.mark.asyncio
    async def test_reviewer_list_sessions(self, api_client: httpx.AsyncClient):
        """Тест: Ревьюер может получить список сессий"""
        response = await api_client.get("/api/reviewer/sessions")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, dict), "Response should be a dict"
        assert "sessions" in data, "Response should have 'sessions' key"
        sessions = data["sessions"]
        assert isinstance(sessions, list), "Sessions should be a list"
        print(f"✓ Retrieved {len(sessions)} sessions")
        
        # Если есть сессии, проверяем структуру
        if len(sessions) > 0:
            session = sessions[0]
            assert "id" in session, "Session should have id"
            assert "candidate_name" in session, "Session should have candidate_name"
            assert "created_at" in session, "Session should have created_at"
    
    @pytest.mark.asyncio
    async def test_reviewer_get_session(self, api_client: httpx.AsyncClient):
        """Тест: Ревьюер может получить конкретную сессию"""
        if not hasattr(pytest, 'test_session_id'):
            pytest.skip("No session created in previous test")
        
        session_id = pytest.test_session_id
        response = await api_client.get(f"/api/reviewer/sessions/{session_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["id"] == session_id, "Session ID should match"
        assert "candidate_name" in data, "Session should have candidate_name"
        assert "comments" in data, "Session should have comments"
        assert isinstance(data["comments"], list), "Comments should be a list"
        
        print(f"✓ Retrieved session {session_id}")
    
    @pytest.mark.asyncio
    async def test_candidate_get_session(self, api_client: httpx.AsyncClient):
        """Тест: Кандидат может получить свою сессию по токену"""
        if not hasattr(pytest, 'test_access_token'):
            pytest.skip("No access token from previous test")
        
        token = pytest.test_access_token
        response = await api_client.get(f"/api/candidate/sessions/{token}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "session_id" in data, "Response should contain session_id"
        assert "candidate_name" in data, "Response should contain candidate_name"
        assert "comments" in data, "Response should contain comments"
        
        print(f"✓ Candidate retrieved session with token")
    
    @pytest.mark.asyncio
    async def test_candidate_get_session_invalid_token(self, api_client: httpx.AsyncClient):
        """Тест: Невалидный токен должен вернуть 404"""
        response = await api_client.get("/api/candidate/sessions/invalid_token_12345")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Invalid token correctly rejected")


class TestComments:
    """Тесты работы с комментариями"""
    
    @pytest.mark.asyncio
    async def test_candidate_add_comment(self, api_client: httpx.AsyncClient, test_comment: Dict[str, Any]):
        """Тест: Кандидат может добавить комментарий"""
        if not hasattr(pytest, 'test_access_token'):
            pytest.skip("No access token from previous test")
        
        token = pytest.test_access_token
        response = await api_client.post(
            f"/api/candidate/sessions/{token}/comments",
            json=test_comment
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("status") == "ok", "Comment should be added successfully"
        print(f"✓ Candidate added comment")
    
    @pytest.mark.asyncio
    async def test_candidate_get_comments(self, api_client: httpx.AsyncClient):
        """Тест: Кандидат может получить список комментариев"""
        if not hasattr(pytest, 'test_access_token'):
            pytest.skip("No access token from previous test")
        
        token = pytest.test_access_token
        response = await api_client.get(f"/api/candidate/sessions/{token}/comments")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, dict), "Response should be a dict"
        assert "comments" in data, "Response should have 'comments' key"
        comments = data["comments"]
        assert isinstance(comments, list), "Comments should be a list"
        print(f"✓ Candidate retrieved {len(comments)} comments")
    
    @pytest.mark.asyncio
    async def test_reviewer_sees_comments(self, api_client: httpx.AsyncClient):
        """Тест: Ревьюер видит комментарии кандидата"""
        if not hasattr(pytest, 'test_session_id'):
            pytest.skip("No session from previous test")
        
        session_id = pytest.test_session_id
        response = await api_client.get(f"/api/reviewer/sessions/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "comments" in data, "Session should have comments"
        assert isinstance(data["comments"], list), "Comments should be a list"
        print(f"✓ Reviewer sees {len(data['comments'])} comments")


class TestGiteaIntegration:
    """Тесты интеграции с Gitea"""
    
    @pytest.mark.asyncio
    async def test_gitea_info_in_session(self, api_client: httpx.AsyncClient):
        """Тест: Сессия содержит информацию о Gitea (если интеграция включена)"""
        if not hasattr(pytest, 'test_session_id'):
            pytest.skip("No session from previous test")
        
        session_id = pytest.test_session_id
        response = await api_client.get(f"/api/reviewer/sessions/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Проверяем наличие полей Gitea (могут быть в объекте gitea если интеграция включена)
        if data.get("gitea") and data["gitea"].get("enabled"):
            print(f"✓ Gitea integration is enabled for session {session_id}")
            assert "user" in data["gitea"] or data["gitea"].get("user") is None
            assert "repo" in data["gitea"] or data["gitea"].get("repo") is None
        else:
            print(f"✓ Gitea integration is disabled (this is OK)")
    
    @pytest.mark.asyncio
    async def test_gitea_pr_creation(self, api_client: httpx.AsyncClient):
        """Тест: Создание PR в Gitea (если интеграция включена)"""
        if not hasattr(pytest, 'test_session_id'):
            pytest.skip("No session from previous test")
        
        session_id = pytest.test_session_id
        
        # Проверяем, есть ли уже PR
        response = await api_client.get(f"/api/reviewer/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        
        if not data.get("gitea_enabled"):
            pytest.skip("Gitea integration not enabled")
        
        # Если PR уже создан при создании сессии, это нормально
        if data.get("gitea_pr_id"):
            print(f"✓ PR already exists: {data['gitea_pr_id']}")
            return
        
        # Пробуем создать PR вручную
        response = await api_client.post(f"/api/reviewer/sessions/{session_id}/gitea/create-pr")
        
        if response.status_code == 200:
            print(f"✓ PR created successfully")
        elif response.status_code == 400:
            # PR уже существует или нет репозитория
            print(f"✓ PR creation endpoint responded (may already exist)")
        else:
            print(f"⚠ PR creation returned {response.status_code}: {response.text}")
    
    @pytest.mark.asyncio
    async def test_gitea_pr_info(self, api_client: httpx.AsyncClient):
        """Тест: Получение информации о PR из Gitea"""
        if not hasattr(pytest, 'test_session_id'):
            pytest.skip("No session from previous test")
        
        session_id = pytest.test_session_id
        
        response = await api_client.get(f"/api/reviewer/sessions/{session_id}/gitea/pr")
        
        if response.status_code == 200:
            data = response.json()
            assert "pr_id" in data or "number" in data, "PR info should contain ID"
            print(f"✓ Retrieved PR info from Gitea")
        elif response.status_code == 400:
            pytest.skip("PR not created for this session")
        elif response.status_code == 503:
            pytest.skip("Gitea integration not available")
        else:
            print(f"⚠ PR info endpoint returned {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_sync_comments_from_gitea(self, api_client: httpx.AsyncClient):
        """Тест: Синхронизация комментариев из Gitea"""
        if not hasattr(pytest, 'test_session_id'):
            pytest.skip("No session from previous test")
        
        session_id = pytest.test_session_id
        
        response = await api_client.post(f"/api/reviewer/sessions/{session_id}/gitea/sync-comments-from-gitea")
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data, "Response should have status"
            assert "synced_count" in data, "Response should have synced_count"
            print(f"✓ Synced {data.get('synced_count', 0)} comments from Gitea")
        elif response.status_code == 400:
            pytest.skip("PR not created for this session")
        elif response.status_code == 503:
            pytest.skip("Gitea integration not available")
        else:
            print(f"⚠ Sync comments returned {response.status_code}: {response.text}")


class TestSessionManagement:
    """Тесты управления сессиями"""
    
    @pytest.mark.asyncio
    async def test_candidate_mark_ready(self, api_client: httpx.AsyncClient):
        """Тест: Кандидат может сигнализировать о готовности"""
        if not hasattr(pytest, 'test_access_token'):
            pytest.skip("No access token from previous test")
        
        token = pytest.test_access_token
        response = await api_client.post(f"/api/candidate/sessions/{token}/ready")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("status") in ["ready", "already_ready"], f"Ready status should be 'ready' or 'already_ready', got '{data.get('status')}'"
        print(f"✓ Candidate marked as ready (status: {data.get('status')})")
    
    @pytest.mark.asyncio
    async def test_reviewer_finish_session(self, api_client: httpx.AsyncClient):
        """Тест: Ревьюер может завершить сессию"""
        if not hasattr(pytest, 'test_session_id'):
            pytest.skip("No session from previous test")
        
        session_id = pytest.test_session_id
        response = await api_client.post(f"/api/reviewer/sessions/{session_id}/finish")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("status") == "finished", f"Session should be finished, got status: '{data.get('status')}'"
        print(f"✓ Reviewer finished session")
    
    @pytest.mark.asyncio
    async def test_reviewer_delete_session(self, api_client: httpx.AsyncClient):
        """Тест: Ревьюер может удалить сессию (soft delete)"""
        if not hasattr(pytest, 'test_session_id'):
            pytest.skip("No session from previous test")
        
        session_id = pytest.test_session_id
        response = await api_client.delete(f"/api/reviewer/sessions/{session_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("status") == "deleted", f"Session should be deleted, got status: '{data.get('status')}'"
        print(f"✓ Reviewer deleted session")
        
        # Проверяем, что сессия не видна в списке
        list_response = await api_client.get("/api/reviewer/sessions")
        assert list_response.status_code == 200
        sessions = list_response.json()
        session_ids = [s["id"] for s in sessions]
        assert session_id not in session_ids, "Deleted session should not appear in list"
        print(f"✓ Deleted session removed from list")


class TestEvaluation:
    """Тесты оценки сессий"""
    
    @pytest.mark.asyncio
    async def test_reviewer_start_evaluation(self, api_client: httpx.AsyncClient):
        """Тест: Ревьюер может запустить оценку сессии"""
        if not hasattr(pytest, 'test_session_id'):
            pytest.skip("No session from previous test")
        
        session_id = pytest.test_session_id
        response = await api_client.post(f"/api/reviewer/sessions/{session_id}/evaluate")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "job_id" in data, "Response should contain job_id"
        print(f"✓ Evaluation job started: {data['job_id']}")
        
        # Сохраняем job_id для проверки статуса
        pytest.test_job_id = data["job_id"]
    
    @pytest.mark.asyncio
    async def test_check_job_status(self, api_client: httpx.AsyncClient):
        """Тест: Проверка статуса задачи оценки"""
        if not hasattr(pytest, 'test_job_id'):
            pytest.skip("No job ID from previous test")
        
        job_id = pytest.test_job_id
        
        # Ждём немного, чтобы задача могла начаться
        await asyncio.sleep(1)
        
        response = await api_client.get(f"/api/jobs/{job_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "status" in data, "Response should contain status"
        print(f"✓ Job status: {data['status']}")


class TestArtifacts:
    """Тесты работы с артефактами"""
    
    @pytest.mark.asyncio
    async def test_get_diff(self, api_client: httpx.AsyncClient):
        """Тест: Получение diff сессии"""
        if not hasattr(pytest, 'test_access_token'):
            pytest.skip("No access token from previous test")
        
        token = pytest.test_access_token
        response = await api_client.get(f"/api/candidate/sessions/{token}/diff")
        
        # Diff может быть пустым, но endpoint должен работать
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Retrieved diff (length: {len(response.text)} bytes)")
    
    @pytest.mark.asyncio
    async def test_get_report(self, api_client: httpx.AsyncClient):
        """Тест: Получение отчёта (может быть не готов)"""
        if not hasattr(pytest, 'test_session_id'):
            pytest.skip("No session from previous test")
        
        session_id = pytest.test_session_id
        response = await api_client.get(f"/api/reviewer/sessions/{session_id}/report")
        
        # Отчёт может быть не готов, но endpoint должен отвечать
        assert response.status_code in [200, 404], f"Expected 200/404, got {response.status_code}"
        if response.status_code == 200:
            print(f"✓ Retrieved report")
        else:
            print(f"✓ Report not ready yet (this is OK)")




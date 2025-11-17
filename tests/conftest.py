"""
Фикстуры для тестов API
"""
import pytest
import httpx
import os
from typing import Dict, Any

# Базовый URL API (можно переопределить через переменную окружения)
# По умолчанию для локального запуска, но внутри Docker сети используем имя сервиса
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture
def api_client():
    """HTTP клиент для тестирования API"""
    return httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0)


@pytest.fixture
def test_reviewer_data() -> Dict[str, str]:
    """Тестовые данные для ревьюера"""
    return {
        "reviewer_name": "Test Reviewer",
        "candidate_name": "Test Candidate",
        "mr_package": "demo_package"
    }


@pytest.fixture
def test_comment() -> Dict[str, Any]:
    """Тестовый комментарий"""
    return {
        "file": "main.py",
        "line_range": "10-15",
        "type": "bug",
        "severity": "high",
        "text": "This is a test comment"
    }


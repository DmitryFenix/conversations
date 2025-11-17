#!/usr/bin/env python3
"""
Ручной запуск тестов без pytest
Для проверки работоспособности API
"""
import asyncio
import httpx
import json
import os
import sys

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")

def print_error(msg):
    print(f"{Colors.RED}✗{Colors.END} {msg}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")

async def test_api_connection():
    """Проверка доступности API"""
    print_info("Testing API connection...")
    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=5.0) as client:
            response = await client.get("/api/reviewer/sessions")
            if response.status_code == 200:
                print_success(f"API is accessible at {API_BASE_URL}")
                return True
            else:
                print_error(f"API returned status {response.status_code}")
                return False
    except httpx.ConnectError:
        print_error(f"Cannot connect to API at {API_BASE_URL}")
        print_info("Make sure the API server is running")
        return False
    except Exception as e:
        print_error(f"Error connecting to API: {e}")
        return False

async def test_create_session():
    """Тест создания сессии"""
    print_info("Testing session creation...")
    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
            payload = {
                "reviewer_name": "Test Reviewer",
                "candidate_name": "Test Candidate",
                "mr_package": "demo_package"
            }
            response = await client.post("/api/reviewer/sessions", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if "session_id" in data and "access_token" in data:
                    print_success(f"Session created: ID={data['session_id']}")
                    return data
                else:
                    print_error("Response missing required fields")
                    return None
            else:
                print_error(f"Failed to create session: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        print_error(f"Error creating session: {e}")
        return None

async def test_get_session(session_id):
    """Тест получения сессии"""
    print_info(f"Testing session retrieval (ID={session_id})...")
    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
            response = await client.get(f"/api/reviewer/sessions/{session_id}")
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"Session retrieved: {data.get('candidate_name', 'N/A')}")
                return True
            else:
                print_error(f"Failed to get session: {response.status_code}")
                return False
    except Exception as e:
        print_error(f"Error getting session: {e}")
        return False

async def test_candidate_access(access_token):
    """Тест доступа кандидата"""
    print_info("Testing candidate access...")
    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
            response = await client.get(f"/api/candidate/sessions/{access_token}")
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"Candidate can access session: {data.get('candidate_name', 'N/A')}")
                return True
            else:
                print_error(f"Candidate access failed: {response.status_code}")
                return False
    except Exception as e:
        print_error(f"Error testing candidate access: {e}")
        return False

async def test_add_comment(access_token):
    """Тест добавления комментария"""
    print_info("Testing comment addition...")
    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
            comment = {
                "file": "main.py",
                "line_range": "10-15",
                "type": "bug",
                "severity": "high",
                "text": "This is a test comment from automated tests"
            }
            response = await client.post(
                f"/api/candidate/sessions/{access_token}/comments",
                json=comment
            )
            
            if response.status_code == 200:
                print_success("Comment added successfully")
                return True
            else:
                print_error(f"Failed to add comment: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        print_error(f"Error adding comment: {e}")
        return False

async def test_list_sessions():
    """Тест получения списка сессий"""
    print_info("Testing session list retrieval...")
    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
            response = await client.get("/api/reviewer/sessions")
            
            if response.status_code == 200:
                sessions = response.json()
                print_success(f"Retrieved {len(sessions)} sessions")
                return True
            else:
                print_error(f"Failed to get sessions: {response.status_code}")
                return False
    except Exception as e:
        print_error(f"Error getting sessions: {e}")
        return False

async def main():
    """Основная функция запуска тестов"""
    print("=" * 80)
    print("API Black Box Tests (Manual Runner)")
    print("=" * 80)
    print(f"API URL: {API_BASE_URL}")
    print()
    
    results = []
    
    # 1. Проверка подключения
    if not await test_api_connection():
        print()
        print_error("Cannot proceed without API connection")
        return 1
    print()
    
    # 2. Создание сессии
    session_data = await test_create_session()
    if not session_data:
        print()
        print_error("Cannot proceed without creating a session")
        return 1
    print()
    
    session_id = session_data["session_id"]
    access_token = session_data["access_token"]
    
    # 3. Получение сессии
    results.append(("Get Session", await test_get_session(session_id)))
    print()
    
    # 4. Доступ кандидата
    results.append(("Candidate Access", await test_candidate_access(access_token)))
    print()
    
    # 5. Добавление комментария
    results.append(("Add Comment", await test_add_comment(access_token)))
    print()
    
    # 6. Список сессий
    results.append(("List Sessions", await test_list_sessions()))
    print()
    
    # Итоги
    print("=" * 80)
    print("Test Results Summary")
    print("=" * 80)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        color = Colors.GREEN if result else Colors.RED
        print(f"{color}{status}{Colors.END} - {test_name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(130)


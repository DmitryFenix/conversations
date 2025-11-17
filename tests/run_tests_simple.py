#!/usr/bin/env python3
"""
Упрощённый скрипт для запуска тестов
Работает даже если pytest не установлен глобально
"""
import subprocess
import sys
import os

def main():
    """Запустить тесты"""
    print("=" * 80)
    print("Running API Tests (Black Box)")
    print("=" * 80)
    print()
    
    # Проверяем доступность API
    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    print(f"API Base URL: {api_url}")
    print()
    
    # Пробуем импортировать зависимости
    try:
        import httpx
        import pytest
        print("✓ Dependencies available")
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print()
        print("Installing dependencies...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "-q", "-r", "tests/requirements.txt"
            ])
            print("✓ Dependencies installed")
        except Exception as install_error:
            print(f"✗ Failed to install dependencies: {install_error}")
            print()
            print("Please install manually:")
            print("  pip install -r tests/requirements.txt")
            return 1
    
    print()
    print("Running tests...")
    print("-" * 80)
    
    # Запускаем pytest
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "tests/test_api.py",
                "-v",
                "--tb=short",
                "--color=yes"
            ],
            env={**os.environ, "API_BASE_URL": api_url}
        )
        return result.returncode
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        return 130
    except Exception as e:
        print(f"\n✗ Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""
Скрипт для непрерывного запуска тестов
Автоматически перезапускает тесты при изменении файлов
"""
import subprocess
import sys
import time
import os
from pathlib import Path

def run_tests():
    """Запустить тесты один раз"""
    print("\n" + "="*80)
    print(f"Running tests at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    print(f"API Base URL: {api_url}\n")
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_api.py", "-v", "--tb=short", "--color=yes"],
        cwd=Path(__file__).parent.parent
    )
    
    return result.returncode == 0

def watch_and_run():
    """Запускать тесты в цикле с задержкой"""
    print("Starting continuous test runner...")
    print("Press Ctrl+C to stop\n")
    
    interval = int(os.getenv("TEST_INTERVAL", "5"))  # Интервал в секундах
    
    try:
        while True:
            run_tests()
            print(f"\nWaiting {interval} seconds before next run...")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\nStopped by user")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Запустить один раз
        success = run_tests()
        sys.exit(0 if success else 1)
    else:
        # Непрерывный режим
        watch_and_run()


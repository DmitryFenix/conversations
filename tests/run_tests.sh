#!/bin/bash
# Скрипт для запуска тестов в watch mode

echo "Starting tests in watch mode..."
echo "API URL: ${API_BASE_URL:-http://localhost:8000}"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Запускаем pytest-watch
pytest-watch tests/test_api.py -v --tb=short


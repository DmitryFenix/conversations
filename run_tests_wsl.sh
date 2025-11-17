#!/bin/bash
# Скрипт для запуска тестов через WSL

set -e

echo "=========================================="
echo "Running API Tests via WSL"
echo "=========================================="
echo ""

# Проверяем, что мы в WSL
if [ -z "$WSL_DISTRO_NAME" ] && [ -z "$WSLENV" ]; then
    echo "⚠ Warning: This script is designed for WSL"
    echo "It may still work, but results may vary"
    echo ""
fi

# Проверяем, что Docker доступен
if ! command -v docker &> /dev/null; then
    echo "✗ Docker is not available"
    echo "Please install Docker or use WSL with Docker"
    exit 1
fi

echo "✓ Docker is available"
echo ""

# Проверяем, что контейнеры запущены
if ! docker compose ps api 2>/dev/null | grep -q "Up"; then
    echo "Starting services..."
    docker compose up -d api redis worker
    echo "Waiting for services to be ready..."
    sleep 10
fi

echo "Running tests..."
echo ""

# Запускаем тесты
docker compose run --rm \
    -e API_BASE_URL=http://api:8000 \
    tests pytest test_api.py test_api_extended.py test_rq_monitoring.py -v --tb=short

echo ""
echo "=========================================="
echo "Tests completed"
echo "=========================================="



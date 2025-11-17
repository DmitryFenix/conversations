#!/bin/bash
# Скрипт для запуска тестов в Docker

set -e

echo "=========================================="
echo "Running API Tests in Docker"
echo "=========================================="
echo ""

# Проверяем, что контейнеры запущены
if ! docker compose ps api | grep -q "Up"; then
    echo "Starting services..."
    docker compose up -d api redis worker
    echo "Waiting for services to be ready..."
    sleep 5
fi

echo "Running tests..."
echo ""

# Запускаем тесты
docker compose run --rm \
    -e API_BASE_URL=http://api:8000 \
    tests

echo ""
echo "=========================================="
echo "Tests completed"
echo "=========================================="


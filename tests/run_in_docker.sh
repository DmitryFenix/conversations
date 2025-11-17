#!/bin/bash
# Простой скрипт для запуска тестов внутри Docker контейнера

echo "Running tests in Docker..."
docker compose run --rm -e API_BASE_URL=http://api:8000 tests


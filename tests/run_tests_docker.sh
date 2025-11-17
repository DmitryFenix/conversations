#!/bin/bash
# Запуск тестов внутри Docker контейнера API

echo "Running tests inside API container..."
docker compose exec api pytest tests/test_api.py -v


#!/bin/bash
# Проверка наличия файлов RQ в контейнере

echo "Checking RQ files in container..."
docker compose exec api ls -la /app/rq*.py
echo ""
echo "Checking if files are importable..."
docker compose exec api python -c "import sys; sys.path.insert(0, '/app'); import rq_monitor; print('✓ rq_monitor imported'); import rq_dashboard; print('✓ rq_dashboard imported')"



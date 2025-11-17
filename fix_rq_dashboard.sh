#!/bin/bash
# Перезапуск API контейнера для подхвата rq_dashboard.py

echo "Restarting API container to pick up rq_dashboard.py..."
docker compose restart api

echo "Waiting for API to start..."
sleep 5

echo "Checking logs for RQ dashboard..."
docker compose logs api --tail=20 | grep -i "rq\|dashboard\|router"

echo ""
echo "Testing endpoint..."
curl -s http://localhost:8000/api/rq/stats || echo "Endpoint not available yet"



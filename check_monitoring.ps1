# Скрипт для проверки статуса мониторинга

Write-Host "=== Проверка основного приложения ===" -ForegroundColor Cyan
docker compose ps

Write-Host "`n=== Проверка RQ Dashboard ===" -ForegroundColor Cyan
docker compose -f docker-compose.monitoring.yml ps

Write-Host "`n=== Проверка сетей Docker ===" -ForegroundColor Cyan
docker network ls | Select-String "conversations"

Write-Host "`n=== Проверка логов RQ Dashboard ===" -ForegroundColor Cyan
docker compose -f docker-compose.monitoring.yml logs --tail=20 rq-dashboard

Write-Host "`n=== Проверка контейнера rq-dashboard ===" -ForegroundColor Cyan
docker ps -a | Select-String "rq-dashboard"


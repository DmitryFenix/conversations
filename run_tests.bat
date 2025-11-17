@echo off
echo ==========================================
echo Running API Tests
echo ==========================================
echo.

REM Проверяем Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo Docker is not available
    exit /b 1
)

echo Starting services...
docker compose up -d api redis worker
timeout /t 5 /nobreak >nul

echo.
echo Running tests...
echo.

docker compose run --rm -e API_BASE_URL=http://api:8000 tests

echo.
echo ==========================================
echo Tests completed
echo ==========================================



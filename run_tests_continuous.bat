@echo off
REM Скрипт для непрерывного запуска тестов в Windows
REM Автоматически перезапускает тесты каждые N секунд

set API_URL=%API_BASE_URL%
if "%API_URL%"=="" set API_URL=http://localhost:8000

set INTERVAL=%TEST_INTERVAL%
if "%INTERVAL%"=="" set INTERVAL=5

echo ==========================================
echo Continuous Test Runner
echo ==========================================
echo API URL: %API_URL%
echo Interval: %INTERVAL% seconds
echo Press Ctrl+C to stop
echo ==========================================
echo.

REM Проверяем, что API доступен
echo Checking API availability...
curl -s -f "%API_URL%/api/reviewer/sessions" >nul 2>&1
if errorlevel 1 (
    echo ERROR: API is not available at %API_URL%
    echo Please make sure the API server is running
    exit /b 1
)
echo [OK] API is available
echo.

REM Устанавливаем зависимости для тестов, если нужно
if not exist "tests\.venv" (
    echo Setting up test environment...
    python -m venv tests\.venv
    tests\.venv\Scripts\pip install -q -r tests\requirements.txt
    echo [OK] Test environment ready
    echo.
)

REM Запускаем тесты в цикле
:loop
    echo ----------------------------------------
    echo Running tests at %date% %time%
    echo ----------------------------------------
    
    set API_BASE_URL=%API_URL%
    tests\.venv\Scripts\pytest tests\test_api.py -v --tb=short
    
    echo.
    echo Waiting %INTERVAL% seconds before next run...
    echo.
    timeout /t %INTERVAL% /nobreak >nul
goto loop


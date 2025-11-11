@echo off
echo ========================================
echo   Sokoni Africa Backend Server
echo ========================================
echo.

REM Get the directory where this script is located
cd /d "%~dp0"

echo Current directory: %CD%
echo.

REM Check if main.py exists
if not exist "main.py" (
    echo ERROR: main.py not found in current directory!
    echo Please make sure you're running this script from the backend directory.
    echo Expected location: sokoni_africa_app\africa_sokoni_app_backend
    pause
    exit /b 1
)

echo Starting FastAPI server...
echo Server will be available at:
echo   - http://localhost:8000
echo   - http://0.0.0.0:8000
echo   - http://192.168.1.186:8000 (your network IP)
echo.
echo Press CTRL+C to stop the server
echo.

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause

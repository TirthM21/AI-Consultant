@echo off
echo ========================================
echo AI Consultant Agent - Quick Setup
echo ========================================
echo.

echo [1/4] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo SUCCESS: Dependencies installed
echo.

echo [2/4] Checking environment configuration...
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo WARNING: Please edit .env file with your email settings
    echo.
)
echo SUCCESS: Environment ready
echo.

echo [3/4] Database will be auto-created on first run...
echo.

echo [4/4] Starting Flask application...
python app.py

pause
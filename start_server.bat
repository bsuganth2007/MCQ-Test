@echo off
echo ========================================
echo   MCQ Test Application - Backend Server
echo ========================================
echo.
echo Starting Flask server on http://localhost:5001
echo Press Ctrl+C to stop
echo.
cd /d "%~dp0backend"
"%~dp0venv\Scripts\python.exe" app.py
pause

@echo off
echo ========================================
echo   Building React Frontend...
echo ========================================
cd /d "%~dp0frontend"
call npm run build
echo.
echo ========================================
echo   Build complete! Start the API server:
echo   python api.py
echo ========================================
pause

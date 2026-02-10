@echo off
chcp 65001 >nul
title Validador de Grados Academicos
echo ══════════════════════════════════════════════════
echo   VALIDADOR DE GRADOS ACADEMICOS - Inicio Total
echo ══════════════════════════════════════════════════
echo.

cd /d "%~dp0"

echo [1/3] Verificando dependencias...
pip install -r requirements.txt --quiet 2>nul

echo [2/3] Iniciando API Server (puerto 8000)...
start "API Server" cmd /c "python api.py"
timeout /t 3 /nobreak >nul

echo [3/3] Iniciando Dashboard Streamlit (puerto 8501)...
start "Dashboard" cmd /c "streamlit run app.py --server.port 8501"
timeout /t 3 /nobreak >nul

echo.
echo ══════════════════════════════════════════════════
echo   Sistema iniciado correctamente:
echo.
echo   API:       http://127.0.0.1:8000
echo   API Docs:  http://127.0.0.1:8000/docs
echo   Dashboard: http://127.0.0.1:8501
echo.
echo   Para detener: cierra las ventanas de terminal.
echo ══════════════════════════════════════════════════
echo.
pause

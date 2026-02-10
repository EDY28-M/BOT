@echo off
chcp 65001 >nul
title Validador de Grados - Dashboard
echo ══════════════════════════════════════════════════
echo   VALIDADOR DE GRADOS ACADEMICOS - Dashboard
echo ══════════════════════════════════════════════════
echo.

cd /d "%~dp0"

echo Iniciando Dashboard Streamlit...
echo Asegurate de que la API este corriendo (iniciar_api.bat)
echo.
streamlit run app.py --server.port 8501
pause

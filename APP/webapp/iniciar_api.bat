@echo off
chcp 65001 >nul
title Validador de Grados - API Server
echo ══════════════════════════════════════════════════
echo   VALIDADOR DE GRADOS ACADEMICOS - API Server
echo ══════════════════════════════════════════════════
echo.

cd /d "%~dp0"

echo [1/2] Verificando dependencias...
python -c "import fastapi, uvicorn, sqlalchemy, botasaurus, pandas" 2>nul
if errorlevel 1 (
    echo [!] Faltan dependencias. Instalando...
    pip install -r requirements.txt
)

echo [2/2] Iniciando API en http://127.0.0.1:8000
echo          Docs en http://127.0.0.1:8000/docs
echo.
echo Presiona Ctrl+C para detener.
echo.
python api.py
pause

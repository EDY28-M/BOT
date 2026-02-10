@echo off
chcp 65001 >nul
title 🎛️ Sistema Completo - ETL Pipeline

echo ╔════════════════════════════════════════════════════════════════╗
echo ║  SISTEMA COMPLETO - Validador de Grados Académicos            ║
echo ║  API + Dashboard Elite (Dark Mode SaaS)                       ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

:: Verificar que estamos en el directorio correcto
if not exist "api.py" (
    echo ❌ Error: No se encontró api.py
    echo ℹ️  Asegúrate de ejecutar este script desde la carpeta webapp
    pause
    exit /b 1
)

echo 🚀 Este script iniciará:
echo    1. API Backend (FastAPI) en http://localhost:8000
echo    2. Dashboard Elite (Streamlit) en http://localhost:8502
echo.
echo ⏳ Iniciando en 3 segundos...
timeout /t 3 /nobreak >nul

:: Crear ventana para la API
start "🌐 API Backend - FastAPI" cmd /k "title API Backend ^&^& echo Iniciando API... ^&^& python api.py"

echo ✅ API iniciada en nueva ventana
echo ⏳ Esperando 5 segundos para que la API inicialice...
timeout /t 5 /nobreak >nul

:: Iniciar Dashboard en esta ventana
echo.
echo 🎨 Iniciando Dashboard Elite...
python -m streamlit run frontwebapp/app_ui.py --server.port=8502 --server.headless=true --theme.base=dark

echo.
echo ❌ Dashboard detenido.
echo ⚠️  La API sigue corriendo en la otra ventana.
pause

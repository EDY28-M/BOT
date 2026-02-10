@echo off
chcp 65001 >nul
title 🚀 Dashboard ETL Elite - Validador de Grados

echo ╔════════════════════════════════════════════════════════════╗
echo ║  DASHBOARD ETL ELITE - Validador de Grados Académicos     ║
echo ║  Interfaz Brutal SaaS Dark Mode + Glassmorphism           ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo 🎨 Características:
echo    • Dark Mode Cyberpunk
echo    • Métricas en tiempo real (Auto-refresh 2s)
echo    • Consola de logs estilo terminal
echo    • Visualización Waterfall del Pipeline
echo.
echo 📡 Conectando a API: http://127.0.0.1:8000
echo 🌐 Dashboard URL: http://localhost:8502
echo.
echo ⚠️  Asegúrate de que la API esté corriendo primero:
echo    ejecuta: iniciar_api.bat
echo.
pause

cd /d "%~dp0.."
echo.
echo 🚀 Iniciando Dashboard Elite...
python -m streamlit run frontwebapp/app_ui.py --server.port=8502 --server.headless=true --theme.base=dark

echo.
echo ❌ Dashboard detenido.
pause

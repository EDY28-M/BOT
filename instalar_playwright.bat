@echo off
chcp 65001 >nul
echo ============================================
echo  INSTALADOR - SUNEDU Playwright + Stealth
echo ============================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado!
    pause
    exit /b 1
)

echo [OK] Python detectado
echo.

echo Instalando dependencias...
echo -----------------------------------------
pip install playwright playwright-stealth pandas openpyxl

echo.
echo Instalando navegador Chromium...
echo -----------------------------------------
playwright install chromium

echo.
echo ============================================
echo  INSTALACION COMPLETADA
echo ============================================
echo.
echo Para ejecutar:
echo   python sunedu_playwright.py dni_lista.csv
echo.
pause

@echo off
chcp 65001 >nul
echo ============================================
echo  INSTALADOR - SUNEDU Botasaurus
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

echo Instalando Botasaurus...
echo -----------------------------------------
pip install botasaurus pandas openpyxl

echo.
echo ============================================
echo  INSTALACION COMPLETADA
echo ============================================
echo.
echo Botasaurus es un framework especializado
echo en evadir deteccion de bots.
echo.
echo Para ejecutar:
echo   python sunedu_botasaurus.py dni_lista.csv
echo.
pause

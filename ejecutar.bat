@echo off
chcp 65001 >nul
echo ============================================
echo  SUNEDU BOT - Iniciando
echo ============================================
echo.

if "%~1"=="" (
    echo Usando archivo por defecto: dni_lista.csv
    echo.
    python sunedu_bot.py
) else (
    echo Usando archivo: %~1
    echo.
    python sunedu_bot.py "%~1"
)

echo.
echo ------------------------------------------
if errorlevel 1 (
    echo [ERROR] El proceso termino con errores
) else (
    echo [OK] Proceso completado
)
echo ------------------------------------------
echo.
echo Presiona cualquier tecla para cerrar...
pause >nul

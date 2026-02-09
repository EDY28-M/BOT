@echo off
chcp 65001 >nul
echo ============================================
echo  INSTALADOR - SUNEDU BOT (Anti-Deteccion)
echo ============================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado!
    echo Descargalo desde: https://python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [OK] Python detectado
echo.

REM Actualizar pip
echo Actualizando pip...
python -m pip install --upgrade pip

echo.
echo Instalando dependencias principales...
echo -----------------------------------------
pip install selenium undetected-chromedriver webdriver-manager
pip install pandas openpyxl xlrd beautifulsoup4 lxml fake-useragent

if errorlevel 1 (
    echo.
    echo [ADVERTENCIA] Algunos paquetes pueden haber fallado
    echo Intentando instalacion individual...
    pip install selenium
    pip install undetected-chromedriver
    pip install pandas openpyxl
)

echo.
echo -----------------------------------------
echo Verificando instalacion...
echo -----------------------------------------
python test_instalacion.py

echo.
echo -----------------------------------------
echo Verificando Chrome y compatibilidad...
echo -----------------------------------------
python verificar_chrome.py

echo.
echo ============================================
echo  INSTALACION COMPLETADA
echo ============================================
echo.
echo Para ejecutar:
echo   python sunedu_bot.py
echo.
echo O arrastra tu archivo CSV sobre ejecutar.bat
echo.
pause

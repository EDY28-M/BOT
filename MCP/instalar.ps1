# Instalador de SUNEDU Scraper (PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  INSTALADOR - SUNEDU Scraper" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] $pythonVersion detectado" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python no está instalado!" -ForegroundColor Red
    Write-Host "Descárgalo desde: https://python.org"
    Read-Host "Presiona Enter para salir"
    exit 1
}

Write-Host ""
Write-Host "Instalando dependencias..." -ForegroundColor Yellow
Write-Host "------------------------------------------"

# Instalar dependencias
try {
    pip install -r requirements.txt
    Write-Host "[OK] Dependencias instaladas" -ForegroundColor Green
} catch {
    Write-Host "Actualizando pip e intentando de nuevo..." -ForegroundColor Yellow
    python -m pip install --upgrade pip
    pip install -r requirements.txt
}

Write-Host ""
Write-Host "------------------------------------------" -ForegroundColor Cyan
Write-Host "Instalando navegador Chromium..." -ForegroundColor Yellow
Write-Host "------------------------------------------"
playwright install chromium

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  INSTALACIÓN COMPLETADA" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para usar:" -ForegroundColor White
Write-Host "  1. Edita dni_lista.csv con tus DNIs" -ForegroundColor Gray
Write-Host "  2. Ejecuta: python sunedu_scraper.py" -ForegroundColor Gray
Write-Host ""
Read-Host "Presiona Enter para salir"

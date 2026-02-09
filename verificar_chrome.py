#!/usr/bin/env python3
"""Verifica la instalación de Chrome y su compatibilidad"""

import os
import sys
import subprocess
import winreg
from pathlib import Path

def obtener_version_chrome():
    """Obtiene la versión de Chrome instalada"""
    versiones = []
    
    # Método 1: Registro
    print("[+] Verificando registro de Windows...")
    reg_paths = [
        (winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Google\Chrome\BLBeacon"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Wow6432Node\Google\Update\Clients\{8A69D345-D564-463c-AFF1-A69D9E530F96}"),
    ]
    
    for hkey, path in reg_paths:
        try:
            reg = winreg.ConnectRegistry(None, hkey)
            key = winreg.OpenKey(reg, path)
            try:
                version, _ = winreg.QueryValueEx(key, "version")
                if version:
                    print(f"   [OK] Version encontrada en registro: {version}")
                    versiones.append(version)
            except:
                try:
                    version, _ = winreg.QueryValueEx(key, "pv")
                    if version:
                        print(f"   [OK] Version encontrada en registro: {version}")
                        versiones.append(version)
                except:
                    pass
        except:
            pass
    
    # Método 2: Ejecutar chrome --version
    print("\n[+] Verificando ejecutable de Chrome...")
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    
    for chrome_path in chrome_paths:
        if os.path.exists(chrome_path):
            print(f"   [OK] Chrome encontrado: {chrome_path}")
            try:
                result = subprocess.run(
                    [chrome_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                output = result.stdout.strip()
                print(f"   [OK] Output: {output}")
                
                if "Chrome" in output:
                    version_str = output.split()[2]
                    versiones.append(version_str)
            except Exception as e:
                print(f"   [ERROR] Error ejecutando: {e}")
        else:
            print(f"   [NO] No encontrado: {chrome_path}")
    
    return versiones

def verificar_undetected_chromedriver():
    """Verifica si undetected_chromedriver puede descargar el driver"""
    print("\n[+] Verificando undetected_chromedriver...")
    
    try:
        import undetected_chromedriver as uc
        print("   [OK] undetected_chromedriver instalado")
        
        # Verificar caché
        cache_dir = Path.home() / ".undetected_chromedriver"
        if cache_dir.exists():
            print(f"   [INFO] Cache encontrado: {cache_dir}")
            chromedrivers = list(cache_dir.glob("chromedriver.exe"))
            if chromedrivers:
                print(f"   [OK] Drivers en cache: {len(chromedrivers)}")
                for driver in chromedrivers:
                    print(f"      - {driver.name}")
            else:
                print("   [WARN] No hay drivers en cache")
        print("   [WARN] No existe directorio de cache")
            
    except ImportError:
        print("   [ERROR] undetected_chromedriver NO instalado")
        return False
    
    return True

def main():
    print("="*70)
    print("  VERIFICACIÓN DE CHROME Y COMPATIBILIDAD")
    print("="*70)
    print()
    
    # Obtener versiones
    versiones = obtener_version_chrome()
    
    print("\n" + "="*70)
    print("  RESULTADOS")
    print("="*70)
    
    if versiones:
        print(f"\n[OK] Chrome instalado - Versiones detectadas:")
        for v in set(versiones):
            version_major = v.split('.')[0]
            print(f"   • {v} (versión principal: {version_major})")
    else:
        print("\n[ERROR] Chrome NO detectado!")
        print("   Descarga Chrome desde: https://google.com/chrome")
        sys.exit(1)
    
    # Verificar undetected_chromedriver
    if not verificar_undetected_chromedriver():
        print("\n[ERROR] Falta instalar undetected_chromedriver")
        print("   Ejecuta: pip install undetected-chromedriver --upgrade")
        sys.exit(1)
    
    # Prueba de conexión
    print("\n[+] Probando conexion con Chrome...")
    try:
        import undetected_chromedriver as uc
        
        version_major = int(versiones[0].split('.')[0])
        print(f"   Intentando iniciar Chrome v{version_major}...")
        
        options = uc.ChromeOptions()
        options.add_argument("--window-size=1920,1080")
        
        driver = uc.Chrome(options=options, version_main=version_major)
        print("   [OK] Chrome iniciado correctamente!")
        
        driver.quit()
        print("   [OK] Chrome cerrado correctamente!")
        
    except Exception as e:
        print(f"   [ERROR] {e}")
        print("\n   Posibles soluciones:")
        print("   1. Cierra todas las ventanas de Chrome")
        print("   2. Ejecuta: pip install undetected-chromedriver --upgrade")
        print("   3. Reinicia tu computadora")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("  [OK] TODO LISTO - Puedes ejecutar python sunedu_bot.py")
    print("="*70)

if __name__ == "__main__":
    main()

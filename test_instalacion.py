#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica que todas las dependencias estén instaladas correctamente"""

import sys

print("="*70)
print("  VERIFICACION DE INSTALACION - SUNEDU BOT")
print("="*70)
print()

# Verificar Python
print(f"✓ Python: {sys.version.split()[0]}")
print()

# Lista de módulos a verificar
modulos = [
    ("selenium", "Control de navegador"),
    ("undetected_chromedriver", "Evasion de deteccion"),
    ("pandas", "Manejo de Excel/CSV"),
    ("openpyxl", "Lectura de Excel"),
    ("bs4", "BeautifulSoup - HTML"),
    ("fake_useragent", "User agents aleatorios"),
]

todo_ok = True

for modulo, descripcion in modulos:
    try:
        __import__(modulo)
        print(f"✓ {modulo:25} - {descripcion}")
    except ImportError:
        print(f"✗ {modulo:25} - FALTA - {descripcion}")
        todo_ok = False

print()

# Verificar undetected_chromedriver específicamente
try:
    import undetected_chromedriver as uc
    print("✓ undetected_chromedriver cargado correctamente")
    
    # Intentar obtener versión
    try:
        print(f"  Version: {uc.__version__ if hasattr(uc, '__version__') else 'N/A'}")
    except:
        pass
        
except Exception as e:
    print(f"✗ Error cargando undetected_chromedriver: {e}")
    todo_ok = False

print()
print("="*70)

if todo_ok:
    print("  ✅ TODO LISTO - Puedes ejecutar: python sunedu_bot.py")
else:
    print("  ❌ FALTAN DEPENDENCIAS")
    print()
    print("  Ejecuta: pip install -r requirements.txt")

print("="*70)
print()

if not todo_ok:
    sys.exit(1)

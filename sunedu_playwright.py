#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUNEDU BOT - Versión Playwright + Stealth
La herramienta más moderna para evadir detección de bots
"""

import os
import sys
import subprocess
import json
import time
import random
import re
import pandas as pd
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict

# Playwright imports
try:
    from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout
    from playwright_stealth import Stealth
except ImportError as e:
    print(f"[!] Error de importacion: {e}")
    print("[i] Ejecuta: pip install playwright playwright-stealth")
    print("[i] Luego: playwright install chromium")
    sys.exit(1)
except Exception as e:
    print(f"[!] Error inesperado: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


@dataclass
class RegistroProfesional:
    """Datos de un registro profesional"""
    dni: str
    nombres: str = ""
    grado_o_titulo: str = ""
    institucion: str = ""
    fecha_diploma: str = ""
    fecha_matricula: str = "Sin información"
    fecha_egreso: str = "Sin información"
    pais: str = "PERU"
    fecha_consulta: str = ""
    estado: str = "PENDIENTE"
    observaciones: str = ""


class SuneduPlaywrightBot:
    """Bot usando Playwright + Stealth para máxima evasión"""
    
    # URLs
    URL_CONSULTA = "https://constanciasweb.sunedu.gob.pe/#/modulos/grados-y-titulos"
    
    # Configuración por defecto
    DEFAULTS = {
        "delay_min": 5,
        "delay_max": 12,
        "timeout_captcha": 180,
        "timeout_pagina": 30,
        "headless": False,
        "guardar_screenshots": True,
        "guardar_cada": 5
    }
    
    def __init__(self, config_file: str = "config.json"):
        """Inicializa el bot"""
        self.config_file = config_file
        self.config = self._cargar_config()
        
        # Directorios
        self.dirs = {
            "output": Path("resultados"),
            "screenshots": Path("screenshots"),
            "logs": Path("logs")
        }
        for d in self.dirs.values():
            d.mkdir(exist_ok=True)
        
        self.resultados: List[RegistroProfesional] = []
        self.playwright = None
        self.browser = None
        self.page = None
        
        self._log("=" * 70)
        self._log("SUNEDU BOT - Playwright + Stealth Mode")
        self._log("=" * 70)
    
    def _cargar_config(self) -> Dict:
        """Carga configuración"""
        config = self.DEFAULTS.copy()
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config.update(json.load(f))
            except Exception as e:
                print(f"[!] Error cargando config: {e}")
        return config
    
    def _log(self, mensaje: str, nivel: str = "INFO"):
        """Guarda log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        linea = f"[{timestamp}] [{nivel}] {mensaje}"
        print(linea)
        
        # Guardar en archivo
        try:
            log_file = self.dirs["logs"] / f"sunedu_{datetime.now().strftime('%Y%m%d')}.log"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(linea + "\n")
        except:
            pass
    
    def _random_delay(self):
        """Espera aleatoria"""
        delay = random.uniform(self.config["delay_min"], self.config["delay_max"])
        time.sleep(delay)
    
    def _tomar_screenshot(self, nombre: str):
        """Toma screenshot si está habilitado"""
        if self.config.get("guardar_screenshots", True) and self.page:
            try:
                path = self.dirs["screenshots"] / f"{nombre}_{datetime.now().strftime('%H%M%S')}.png"
                self.page.screenshot(path=str(path))
            except:
                pass
    
    def iniciar_navegador(self) -> bool:
        """Inicia navegador con Playwright + Stealth"""
        self._log("Iniciando navegador con Playwright + Stealth...")
        
        try:
            self.playwright = sync_playwright().start()
            
            # Launch options
            launch_options = {
                "headless": self.config.get("headless", False),
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-extensions",
                    "--window-size=1366,768"
                ]
            }
            
            self.browser = self.playwright.chromium.launch(**launch_options)
            
            # Crear contexto con user agent real
            context = self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale="es-PE",
                timezone_id="America/Lima"
            )
            
            self.page = context.new_page()
            
            # Aplicar STEALTH - esto oculta que es automatizacion
            stealth = Stealth()
            stealth.apply_stealth_sync(self.page)
            
            self._log("[OK] Navegador iniciado con Stealth mode activado")
            return True
            
        except Exception as e:
            self._log(f"Error iniciando navegador: {e}", "ERROR")
            return False
    
    def cerrar_navegador(self):
        """Cierra navegador"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except:
            pass
    
    def navegar(self) -> bool:
        """Navega a SUNEDU"""
        try:
            self._log("Navegando a SUNEDU...")
            self.page.goto(self.URL_CONSULTA, wait_until="networkidle")
            time.sleep(3)
            self._log("[OK] Página cargada")
            return True
        except Exception as e:
            self._log(f"Error navegando: {e}", "ERROR")
            return False
    
    def detectar_captcha(self) -> bool:
        """Detecta CAPTCHA en la página"""
        try:
            # Buscar elementos de CAPTCHA/Turnstile
            captcha_selectors = [
                ".cf-turnstile",
                ".cf-challenge",
                "[data-cf-turnstile]",
                "iframe[src*='challenges.cloudflare']",
                "iframe[src*='turnstile']",
                ".h-captcha",
                ".g-recaptcha"
            ]
            
            for selector in captcha_selectors:
                try:
                    element = self.page.locator(selector).first
                    if element.is_visible():
                        return True
                except:
                    continue
            
            # Verificar texto
            page_text = self.page.content().lower()
            if any(x in page_text for x in ['captcha', 'turnstile', 'cloudflare']):
                return True
            
            return False
        except:
            return False
    
    def ingresar_dni(self, dni: str) -> bool:
        """Ingresa DNI en el formulario"""
        try:
            # Buscar campo de DNI
            selectores = [
                "input[placeholder*='DNI' i]",
                "input[name*='dni' i]",
                "input[type='text']",
                "input.form-control"
            ]
            
            for selector in selectores:
                try:
                    input_field = self.page.locator(selector).first
                    if input_field.is_visible():
                        input_field.fill("")
                        input_field.fill(str(dni))
                        self._log(f"[OK] DNI {dni} ingresado")
                        return True
                except:
                    continue
            
            return False
        except Exception as e:
            self._log(f"Error ingresando DNI: {e}", "ERROR")
            return False
    
    def hacer_click_buscar(self) -> bool:
        """Hace clic en botón Buscar"""
        try:
            botones = [
                "button:has-text('Buscar')",
                "button[type='submit']",
                "button.btn-primary"
            ]
            
            for selector in botones:
                try:
                    btn = self.page.locator(selector).first
                    if btn.is_visible():
                        btn.click()
                        time.sleep(2)
                        return True
                except:
                    continue
            
            # Si no hay botón, presionar Enter
            self.page.keyboard.press("Enter")
            return True
        except:
            return False
    
    def esperar_captcha_manual(self, dni: str) -> bool:
        """Espera que el usuario resuelva CAPTCHA"""
        print("\n" + "="*70)
        print(f"[CAPTCHA] DNI: {dni}")
        print("="*70)
        print("""
[ACCION REQUERIDA]:
  1. En la ventana del navegador, completa el CAPTCHA
  2. Haz clic en "Buscar" si es necesario
  3. Espera a que aparezcan los resultados
  4. Vuelve aquí y presiona ENTER
""")
        print(f"[Tiempo] Tienes {self.config['timeout_captcha']} segundos")
        print("="*70)
        
        try:
            input("\n[ENTER] Presiona ENTER cuando termines (o 's' para saltar): ")
            time.sleep(2)
            return True
        except:
            return False
    
    def extraer_datos(self, dni: str) -> List[RegistroProfesional]:
        """Extrae datos de la tabla"""
        registros = []
        
        try:
            time.sleep(3)
            self._tomar_screenshot(f"{dni}_extraccion")
            
            # Buscar filas de resultados
            filas = self.page.locator("table tbody tr, tr.ng-star-inserted").all()
            
            if not filas:
                content = self.page.content()
                if any(x in content.lower() for x in ["no se encontraron", "sin resultados"]):
                    registros.append(RegistroProfesional(
                        dni=dni,
                        estado="NO ENCONTRADO",
                        fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                    return registros
            
            self._log(f"Encontradas {len(filas)} filas")
            
            for i, fila in enumerate(filas, 1):
                try:
                    celdas = fila.locator("td").all()
                    if len(celdas) < 3:
                        continue
                    
                    # Celda 1: Nombre
                    texto_c1 = celdas[0].inner_text()
                    nombres = ""
                    for linea in texto_c1.split('\n'):
                        linea = linea.strip()
                        if ',' in linea and len(linea) > 5:
                            nombres = linea
                            break
                    if not nombres:
                        for linea in texto_c1.split('\n'):
                            if linea.isupper() and len(linea) > 5:
                                nombres = linea
                                break
                    
                    # Celda 2: Grado y fechas
                    texto_c2 = celdas[1].inner_text()
                    lineas_c2 = [l.strip() for l in texto_c2.split('\n') if l.strip()]
                    
                    grado_titulo = lineas_c2[0] if lineas_c2 else ""
                    fecha_diploma = ""
                    fecha_matricula = "Sin información"
                    fecha_egreso = "Sin información"
                    
                    for linea in lineas_c2:
                        ll = linea.lower()
                        if 'diploma:' in ll:
                            fecha_diploma = linea.split(':', 1)[-1].strip()
                        elif 'matricula:' in ll or 'matrícula:' in ll:
                            fecha_matricula = linea.split(':', 1)[-1].strip()
                        elif 'egreso:' in ll:
                            fecha_egreso = linea.split(':', 1)[-1].strip()
                    
                    # Celda 3: Institución
                    texto_c3 = celdas[2].inner_text()
                    lineas_c3 = [l.strip() for l in texto_c3.split('\n') if l.strip()]
                    
                    institucion = ""
                    for linea in lineas_c3:
                        if any(p in linea.upper() for p in ['UNIVERSIDAD', 'INSTITUTO']):
                            institucion = linea
                            break
                    if not institucion:
                        for linea in lineas_c3:
                            if linea.isupper() and len(linea) > 3:
                                institucion = linea
                                break
                    
                    # Buscar país
                    pais = "PERU"
                    for linea in lineas_c3:
                        if 'PERU' in linea.upper():
                            pais = "PERU"
                            break
                    
                    if nombres or grado_titulo:
                        registro = RegistroProfesional(
                            dni=dni,
                            nombres=nombres,
                            grado_o_titulo=grado_titulo,
                            institucion=institucion,
                            fecha_diploma=fecha_diploma,
                            fecha_matricula=fecha_matricula,
                            fecha_egreso=fecha_egreso,
                            pais=pais,
                            fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            estado="ENCONTRADO"
                        )
                        registros.append(registro)
                        self._log(f"  [OK] {grado_titulo[:50] if grado_titulo else nombres[:50]}...")
                
                except Exception as e:
                    self._log(f"  Error fila {i}: {e}", "WARNING")
                    continue
            
        except Exception as e:
            self._log(f"Error extrayendo: {e}", "ERROR")
        
        return registros
    
    def consultar_dni(self, dni: str) -> List[RegistroProfesional]:
        """Consulta un DNI"""
        self._log("\n" + "="*70)
        self._log(f"CONSULTANDO DNI: {dni}")
        self._log("="*70)
        
        try:
            # Navegar
            if not self.navegar():
                return []
            
            # Ingresar DNI
            if not self.ingresar_dni(dni):
                return []
            
            # Click buscar
            self.hacer_click_buscar()
            time.sleep(3)
            
            # Detectar CAPTCHA
            if self.detectar_captcha():
                self._tomar_screenshot(f"{dni}_captcha")
                if not self.esperar_captcha_manual(dni):
                    return []
            
            # Extraer datos
            registros = self.extraer_datos(dni)
            return registros
            
        except Exception as e:
            self._log(f"Error consultando: {e}", "ERROR")
            return []
    
    def procesar_lista(self, archivo: str):
        """Procesa lista de DNIs"""
        dnis = self._leer_dnis(archivo)
        if not dnis:
            self._log("No se encontraron DNIs")
            return
        
        self._log(f"Total DNIs a procesar: {len(dnis)}")
        
        if not self.iniciar_navegador():
            return
        
        try:
            for i, dni in enumerate(dnis, 1):
                registros = self.consultar_dni(dni)
                self.resultados.extend(registros)
                
                if i % self.config.get("guardar_cada", 5) == 0:
                    self._guardar_resultados(f"_progreso_{i}")
                
                if i < len(dnis):
                    self._random_delay()
        
        except KeyboardInterrupt:
            self._log("Interrumpido por usuario")
        
        finally:
            self.cerrar_navegador()
            self._guardar_resultados("_final")
    
    def _leer_dnis(self, archivo: str) -> List[str]:
        """Lee DNIs"""
        dnis = []
        path = Path(archivo)
        
        if not path.exists():
            return []
        
        try:
            if archivo.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(archivo, dtype=str)
            else:
                df = pd.read_csv(archivo, dtype=str)
            
            for col in df.columns:
                if col.upper() in ['DNI', 'DOCUMENTO']:
                    dnis = df[col].dropna().astype(str).str.strip().tolist()
                    break
            
            dnis = [d for d in dnis if d.isdigit()]
            dnis = list(dict.fromkeys(dnis))
            
        except Exception as e:
            self._log(f"Error leyendo archivo: {e}")
        
        return dnis
    
    def _guardar_resultados(self, sufijo: str = ""):
        """Guarda resultados"""
        if not self.resultados:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        datos = [asdict(r) for r in self.resultados]
        df = pd.DataFrame(datos)
        
        excel_path = self.dirs["output"] / f"SUNEDU_PW{sufijo}_{timestamp}.xlsx"
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
        csv_path = self.dirs["output"] / f"SUNEDU_PW{sufijo}_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        self._log(f"[OK] Guardado: {excel_path.name}")


def main():
    print("="*70)
    print("  SUNEDU BOT - Playwright + Stealth")
    print("="*70)
    
    archivo = sys.argv[1] if len(sys.argv) > 1 else "dni_lista.csv"
    
    bot = SuneduPlaywrightBot()
    bot.procesar_lista(archivo)
    
    print("\n" + "="*70)
    print("[OK] PROCESO FINALIZADO")
    print("="*70)


if __name__ == "__main__":
    main()

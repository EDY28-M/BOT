#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUNEDU Scraper - Automatización de consulta de grados y títulos
Extrae información de profesionales desde la web de SUNEDU Perú
"""

import json
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout


@dataclass
class RegistroProfesional:
    """Clase para almacenar datos de un registro profesional"""
    dni: str
    nombres: str
    grado_o_titulo: str
    institucion: str
    fecha_diploma: str
    fecha_matricula: str = "Sin información"
    fecha_egreso: str = "Sin información"
    pais: str = "PERU"
    fecha_consulta: str = ""
    estado: str = ""
    observaciones: str = ""


class SuneduScraper:
    """Scraper para la web de SUNEDU"""
    
    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.resultados: List[RegistroProfesional] = []
        self.url = self.config.get("url", "https://constanciasweb.sunedu.gob.pe/#/modulos/grados-y-titulos")
        self.timeout_captcha = self.config.get("timeout_captcha", 120)
        self.delay = self.config.get("delay_entre_consultas", 3)
        self.headless = self.config.get("headless", False)
        self.guardar_screenshots = self.config.get("guardar_screenshots", True)
        
        # Crear carpeta de resultados
        self.output_dir = Path("resultados")
        self.output_dir.mkdir(exist_ok=True)
        self.screenshots_dir = Path("screenshots")
        if self.guardar_screenshots:
            self.screenshots_dir.mkdir(exist_ok=True)
    
    def iniciar_navegador(self):
        """Inicia el navegador con Playwright"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(30000)
    
    def cerrar_navegador(self):
        """Cierra el navegador"""
        if hasattr(self, 'context'):
            self.context.close()
        if hasattr(self, 'browser'):
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()
    
    def esperar_captcha_manual(self, dni: str) -> bool:
        """
        Espera a que el usuario resuelva el CAPTCHA manualmente.
        Retorna True si se resolvió, False si timeout.
        """
        print(f"\n{'='*60}")
        print(f"DNI A CONSULTAR: {dni}")
        print(f"{'='*60}")
        print("\n⚠️  ACCIÓN REQUERIDA:")
        print("   1. Completa el CAPTCHA en la página (si aparece)")
        print("   2. Presiona ENTER en esta consola cuando termines...")
        print(f"\n⏱️  Tienes {self.timeout_captcha} segundos...")
        
        try:
            # Usar input con timeout sería complejo, así que usamos un enfoque simple
            # El usuario debe presionar Enter cuando termine
            import threading
            
            resultado = [None]
            def esperar_input():
                try:
                    input("\n👉 Presiona ENTER cuando hayas completado el CAPTCHA... ")
                    resultado[0] = True
                except:
                    resultado[0] = False
            
            hilo = threading.Thread(target=esperar_input)
            hilo.daemon = True
            hilo.start()
            hilo.join(timeout=self.timeout_captcha)
            
            if resultado[0] is None:
                print("\n❌ Timeout! No se recibió confirmación.")
                return False
            
            # Pequeña pausa para asegurar que la página procesó
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"\n❌ Error esperando CAPTCHA: {e}")
            return False
    
    def esperar_resultados(self, timeout: int = 30) -> bool:
        """Espera a que aparezcan los resultados en la tabla"""
        try:
            # Esperar a que aparezca la tabla de resultados
            self.page.wait_for_selector("table.custom-table tbody tr", timeout=timeout*1000)
            return True
        except PlaywrightTimeout:
            return False
    
    def extraer_datos(self, dni: str) -> List[RegistroProfesional]:
        """Extrae los datos de la tabla de resultados"""
        registros = []
        
        try:
            # Buscar todas las filas de resultados
            filas = self.page.query_selector_all("table.custom-table tbody tr.ng-star-inserted")
            
            print(f"   📊 Se encontraron {len(filas)} registro(s) para el DNI {dni}")
            
            for i, fila in enumerate(filas, 1):
                try:
                    # Extraer datos de cada celda
                    celdas = fila.query_selector_all("td")
                    if len(celdas) < 3:
                        continue
                    
                    # Celda 1: Datos del graduado
                    nombre_elem = celdas[0].query_selector("p")
                    nombres = nombre_elem.inner_text().strip() if nombre_elem else ""
                    
                    # Celda 2: Grado/Título
                    titulo_elem = celdas[1].query_selector("p.poppins-bold")
                    grado_titulo = titulo_elem.inner_text().strip() if titulo_elem else ""
                    
                    # Fechas
                    fechas = celdas[1].query_selector_all("p")
                    fecha_diploma = ""
                    fecha_matricula = "Sin información"
                    fecha_egreso = "Sin información"
                    
                    for f in fechas:
                        texto = f.inner_text()
                        if "Fecha de diploma:" in texto:
                            fecha_diploma = texto.replace("Fecha de diploma:", "").strip()
                        elif "Fecha matrícula:" in texto:
                            fecha_matricula = texto.replace("Fecha matrícula:", "").strip()
                        elif "Fecha egreso:" in texto:
                            fecha_egreso = texto.replace("Fecha egreso:", "").strip()
                    
                    # Celda 3: Institución
                    inst_elem = celdas[2].query_selector("p.font-bold")
                    institucion = inst_elem.inner_text().strip() if inst_elem else ""
                    
                    # Crear registro
                    registro = RegistroProfesional(
                        dni=dni,
                        nombres=nombres,
                        grado_o_titulo=grado_titulo,
                        institucion=institucion,
                        fecha_diploma=fecha_diploma,
                        fecha_matricula=fecha_matricula,
                        fecha_egreso=fecha_egreso,
                        fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        estado="ENCONTRADO"
                    )
                    registros.append(registro)
                    
                    print(f"   ✅ Registro {i}: {grado_titulo}")
                    
                except Exception as e:
                    print(f"   ⚠️  Error extrayendo fila {i}: {e}")
                    continue
                    
        except Exception as e:
            print(f"   ❌ Error general extrayendo datos: {e}")
        
        return registros
    
    def verificar_sin_resultados(self) -> bool:
        """Verifica si apareció el mensaje de 'sin resultados'"""
        try:
            # Buscar mensaje de no encontrado o similar
            mensajes_no_encontrado = [
                "no se encontraron",
                "sin resultados",
                "no existe",
                "no registra"
            ]
            
            page_text = self.page.content().lower()
            for mensaje in mensajes_no_encontrado:
                if mensaje in page_text:
                    return True
            
            return False
        except:
            return False
    
    def consultar_dni(self, dni: str) -> List[RegistroProfesional]:
        """Realiza la consulta de un DNI específico"""
        registros = []
        
        try:
            # Navegar a la página
            print(f"\n🌐 Navegando a SUNEDU...")
            self.page.goto(self.url, wait_until="networkidle")
            time.sleep(2)
            
            # Tomar screenshot inicial
            if self.guardar_screenshots:
                self.page.screenshot(path=str(self.screenshots_dir / f"{dni}_inicio.png"))
            
            # Buscar el campo de DNI - probamos varios selectores posibles
            selectores_dni = [
                "input[placeholder*='DNI']",
                "input[name*='dni']",
                "input[id*='dni']",
                "input[type='text']",
                "input.form-control",
                "input.p-inputtext"
            ]
            
            campo_dni = None
            for selector in selectores_dni:
                try:
                    campo_dni = self.page.query_selector(selector)
                    if campo_dni:
                        # Verificar que sea visible y editable
                        if campo_dni.is_visible() and campo_dni.is_enabled():
                            break
                except:
                    continue
            
            if not campo_dni:
                print("   ❌ No se encontró el campo de DNI")
                return []
            
            # Limpiar e ingresar DNI
            campo_dni.click()
            campo_dni.fill("")
            time.sleep(0.5)
            campo_dni.fill(dni)
            print(f"   ✏️  DNI ingresado: {dni}")
            
            # Buscar botón de búsqueda
            selectores_boton = [
                "button:has-text('Buscar')",
                "button:has-text('Consultar')",
                "button[type='submit']",
                "button.btn-primary",
                "button.p-button"
            ]
            
            boton_buscar = None
            for selector in selectores_boton:
                try:
                    boton_buscar = self.page.query_selector(selector)
                    if boton_buscar and boton_buscar.is_visible():
                        break
                except:
                    continue
            
            if boton_buscar:
                print("   🔍 Haciendo clic en Buscar...")
                boton_buscar.click()
            else:
                # Si no hay botón visible, presionar Enter
                print("   🔍 Presionando Enter...")
                campo_dni.press("Enter")
            
            # Esperar a que aparezca el CAPTCHA o los resultados
            time.sleep(2)
            
            # Verificar si hay CAPTCHA
            captcha_detectado = self.detectar_captcha()
            
            if captcha_detectado:
                print("   🔒 CAPTCHA detectado!")
                if self.guardar_screenshots:
                    self.page.screenshot(path=str(self.screenshots_dir / f"{dni}_captcha.png"))
                
                # Esperar resolución manual
                if not self.esperar_captcha_manual(dni):
                    print("   ❌ No se resolvió el CAPTCHA")
                    return []
            
            # Esperar resultados
            print("   ⏳ Esperando resultados...")
            time.sleep(3)
            
            # Verificar si hay resultados
            if self.esperar_resultados(timeout=10):
                if self.guardar_screenshots:
                    self.page.screenshot(path=str(self.screenshots_dir / f"{dni}_resultados.png"))
                
                registros = self.extraer_datos(dni)
            
            elif self.verificar_sin_resultados():
                print(f"   ⚠️  No se encontraron registros para el DNI {dni}")
                registro_vacio = RegistroProfesional(
                    dni=dni,
                    nombres="",
                    grado_o_titulo="",
                    institucion="",
                    fecha_diploma="",
                    fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    estado="NO ENCONTRADO"
                )
                registros.append(registro_vacio)
            
            else:
                print(f"   ⚠️  No se pudo determinar el estado de la consulta")
                # Intentar screenshot de diagnóstico
                if self.guardar_screenshots:
                    self.page.screenshot(path=str(self.screenshots_dir / f"{dni}_diagnostico.png"))
            
        except Exception as e:
            print(f"   ❌ Error en consulta: {e}")
            import traceback
            traceback.print_exc()
        
        return registros
    
    def detectar_captcha(self) -> bool:
        """Detecta si hay un CAPTCHA en la página"""
        indicadores_captcha = [
            ".g-recaptcha",
            "[data-sitekey]",
            "iframe[src*='recaptcha']",
            "iframe[src*='captcha']",
            ".h-captcha",
            "#captcha",
            "text=CAPTCHA",
            "text=captcha"
        ]
        
        for indicador in indicadores_captcha:
            try:
                elemento = self.page.query_selector(indicador)
                if elemento and elemento.is_visible():
                    return True
            except:
                continue
        
        return False
    
    def procesar_lista_dnis(self, archivo_entrada: str) -> None:
        """Procesa una lista de DNIs desde un archivo"""
        # Leer DNIs
        dnis = self.leer_dnis(archivo_entrada)
        
        if not dnis:
            print("❌ No se encontraron DNIs para procesar")
            return
        
        print(f"\n{'='*60}")
        print(f"📋 TOTAL DE DNIs A PROCESAR: {len(dnis)}")
        print(f"{'='*60}")
        
        # Iniciar navegador
        self.iniciar_navegador()
        
        try:
            for i, dni in enumerate(dnis, 1):
                print(f"\n{'─'*60}")
                print(f"📌 Procesando {i}/{len(dnis)}: DNI {dni}")
                print(f"{'─'*60}")
                
                registros = self.consultar_dni(dni)
                self.resultados.extend(registros)
                
                # Guardar progreso parcial cada 5 registros
                if i % 5 == 0:
                    self.guardar_resultados(sufijo="_parcial")
                
                # Delay entre consultas
                if i < len(dnis):
                    print(f"   ⏱️  Esperando {self.delay} segundos...")
                    time.sleep(self.delay)
        
        finally:
            # Cerrar navegador
            self.cerrar_navegador()
            
            # Guardar resultados finales
            self.guardar_resultados()
    
    def leer_dnis(self, archivo: str) -> List[str]:
        """Lee DNIs desde un archivo Excel o CSV"""
        dnis = []
        path = Path(archivo)
        
        if not path.exists():
            print(f"❌ Archivo no encontrado: {archivo}")
            return dnis
        
        try:
            if archivo.endswith('.xlsx') or archivo.endswith('.xls'):
                df = pd.read_excel(archivo)
                # Buscar columna DNI (case insensitive)
                for col in df.columns:
                    if col.upper() == 'DNI':
                        dnis = df[col].dropna().astype(str).str.strip().tolist()
                        break
            
            elif archivo.endswith('.csv'):
                df = pd.read_csv(archivo)
                for col in df.columns:
                    if col.upper() == 'DNI':
                        dnis = df[col].dropna().astype(str).str.strip().tolist()
                        break
            
            # Limpiar DNIs (solo números)
            dnis = [d.strip() for d in dnis if d.strip().isdigit()]
            # Remover duplicados manteniendo orden
            dnis = list(dict.fromkeys(dnis))
            
        except Exception as e:
            print(f"❌ Error leyendo archivo: {e}")
        
        return dnis
    
    def guardar_resultados(self, sufijo: str = "") -> None:
        """Guarda los resultados en Excel y CSV"""
        if not self.resultados:
            print("⚠️  No hay resultados para guardar")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Convertir a DataFrame
        datos = [asdict(r) for r in self.resultados]
        df = pd.DataFrame(datos)
        
        # Reordenar columnas
        columnas_orden = [
            'dni', 'nombres', 'grado_o_titulo', 'institucion',
            'fecha_diploma', 'fecha_matricula', 'fecha_egreso',
            'pais', 'estado', 'fecha_consulta', 'observaciones'
        ]
        
        df = df[[col for col in columnas_orden if col in df.columns]]
        
        # Guardar Excel
        excel_path = self.output_dir / f"resultados_sunedu{sufijo}_{timestamp}.xlsx"
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
        # Guardar CSV
        csv_path = self.output_dir / f"resultados_sunedu{sufijo}_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        print(f"\n💾 Resultados guardados:")
        print(f"   📊 Excel: {excel_path}")
        print(f"   📄 CSV: {csv_path}")


def main():
    """Función principal"""
    print("="*70)
    print("     SUNEDU SCRAPER - Consulta de Grados y Títulos")
    print("     Superintendencia Nacional de Educación Superior Universitaria")
    print("="*70)
    
    # Verificar argumentos
    import sys
    
    archivo_entrada = "dni_lista.csv"
    if len(sys.argv) > 1:
        archivo_entrada = sys.argv[1]
    
    print(f"\n📁 Archivo de entrada: {archivo_entrada}")
    
    # Crear instancia del scraper
    scraper = SuneduScraper()
    
    # Procesar
    try:
        scraper.procesar_lista_dnis(archivo_entrada)
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
        scraper.guardar_resultados(sufijo="_interrumpido")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*70)
    print("                    PROCESO FINALIZADO")
    print("="*70)


if __name__ == "__main__":
    main()

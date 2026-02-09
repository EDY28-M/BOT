#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUNEDU BOT - Versión Microsoft Edge
Usa Edge en lugar de Chrome para evadir detección de Cloudflare
"""

import os
import json
import time
import random
import pandas as pd
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.common.exceptions import TimeoutException, NoSuchElementException


@dataclass
class RegistroProfesional:
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


class SuneduEdgeBot:
    """Bot usando Microsoft Edge"""
    
    def __init__(self):
        self.resultados: List[RegistroProfesional] = []
        self.driver = None
        self.wait = None
        
        self.url = "https://constanciasweb.sunedu.gob.pe/#/modulos/grados-y-titulos"
        
        # Directorios
        self.output_dir = Path("resultados")
        self.output_dir.mkdir(exist_ok=True)
        self.screenshots_dir = Path("screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
        
        # Estadísticas
        self.stats = {"total": 0, "exitosos": 0, "no_encontrados": 0, "errores": 0}
    
    def _log(self, mensaje: str, tipo: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{tipo}] {mensaje}")
    
    def iniciar_navegador(self):
        """Inicia Microsoft Edge con configuración anti-detección"""
        self._log("Iniciando Microsoft Edge...")
        
        try:
            options = EdgeOptions()
            
            # === CONFIGURACIÓN ANTI-DETECCIÓN ===
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--window-size=1366,768")
            options.add_argument("--start-maximized")
            
            # User agent de Edge real
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")
            
            # Idioma
            options.add_argument("--lang=es-PE")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Crear perfil temporal LIMPIO (no usar perfil existente)
            import tempfile
            temp_dir = tempfile.mkdtemp(prefix="edge_profile_")
            options.add_argument(f"--user-data-dir={temp_dir}")
            self._log(f"Usando perfil temporal: {temp_dir}")
            
            # Iniciar Edge
            self.driver = webdriver.Edge(options=options)
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 20)
            
            # Ocultar webdriver
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
            """)
            
            self._log("[OK] Edge iniciado correctamente")
            return True
            
        except Exception as e:
            self._log(f"Error iniciando Edge: {e}", "ERROR")
            self._log("Intentando método alternativo...", "WARNING")
            
            # Método alternativo: sin opciones avanzadas
            try:
                options = EdgeOptions()
                options.add_argument("--window-size=1366,768")
                
                # Crear perfil temporal
                import tempfile
                temp_dir = tempfile.mkdtemp(prefix="edge_profile_")
                options.add_argument(f"--user-data-dir={temp_dir}")
                
                self.driver = webdriver.Edge(options=options)
                self.wait = WebDriverWait(self.driver, 20)
                self._log("[OK] Edge iniciado (método alternativo)")
                return True
            except Exception as e2:
                self._log(f"Error fatal: {e2}", "ERROR")
                self._log("Asegurate de tener Edge instalado y actualizado", "WARNING")
                self._log("Descarga Edge desde: https://www.microsoft.com/edge", "INFO")
                return False
    
    def cerrar_navegador(self):
        """Cierra Edge de forma segura"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def navegar(self):
        """Navega a la página de SUNEDU"""
        try:
            self._log("Navegando a SUNEDU...")
            self.driver.get(self.url)
            time.sleep(5)
            self._log("[OK] Página cargada")
            return True
        except Exception as e:
            self._log(f"Error navegando: {e}", "ERROR")
            return False
    
    def modo_manual(self, dni: str) -> List[RegistroProfesional]:
        """Modo manual: tú ingresas datos y CAPTCHA"""
        registros = []
        
        print("\n" + "="*70)
        print(f"MODO MANUAL - DNI: {dni}")
        print("="*70)
        print("""
[INSTRUCCIONES]:
  1. En la ventana de Edge, ingresa el DNI manualmente
  2. Resuelve el CAPTCHA (marca "No soy un robot")
  3. Haz clic en "Buscar"
  4. Espera a que aparezcan los resultados
  5. Vuelve aquí y presiona ENTER
""")
        print("="*70)
        
        try:
            respuesta = input("\n[ENTER] Presiona ENTER cuando veas los resultados (o 's' para saltar): ")
            
            if respuesta.lower() == 's':
                return []
            
            time.sleep(2)
            
            # Extraer datos
            registros = self.extraer_datos(dni)
            
        except KeyboardInterrupt:
            self._log("Interrumpido por usuario", "WARNING")
        
        return registros
    
    def extraer_datos(self, dni: str) -> List[RegistroProfesional]:
        """Extrae datos de la tabla de resultados"""
        registros = []
        
        try:
            # Screenshot
            self.driver.save_screenshot(str(self.screenshots_dir / f"{dni}_resultado.png"))
            
            time.sleep(3)
            
            # Buscar tabla
            filas = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr, .tabla-resultados tbody tr, tr.ng-star-inserted")
            
            if not filas:
                page_text = self.driver.page_source.lower()
                if any(x in page_text for x in ["no se encontraron", "sin resultados"]):
                    registros.append(RegistroProfesional(
                        dni=dni,
                        estado="NO ENCONTRADO",
                        fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                    return registros
            
            self._log(f"Encontradas {len(filas)} filas")
            
            for i, fila in enumerate(filas):
                try:
                    celdas = fila.find_elements(By.TAG_NAME, "td")
                    if len(celdas) < 3:
                        continue
                    
                    nombres = celdas[0].text.strip().split('\n')[0] if len(celdas) > 0 else ""
                    
                    texto_celda2 = celdas[1].text if len(celdas) > 1 else ""
                    lineas = [l.strip() for l in texto_celda2.split('\n') if l.strip()]
                    
                    grado_titulo = lineas[0] if lineas else ""
                    fecha_diploma = ""
                    fecha_matricula = "Sin información"
                    fecha_egreso = "Sin información"
                    
                    for linea in lineas:
                        if "diploma:" in linea.lower():
                            fecha_diploma = linea.split(":", 1)[-1].strip()
                        elif "matrícula:" in linea.lower():
                            fecha_matricula = linea.split(":", 1)[-1].strip()
                        elif "egreso:" in linea.lower():
                            fecha_egreso = linea.split(":", 1)[-1].strip()
                    
                    institucion = celdas[2].text.strip().split('\n')[0] if len(celdas) > 2 else ""
                    
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
                    self._log(f"  [OK] Registro: {grado_titulo[:50]}...")
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            self._log(f"Error extrayendo: {e}", "ERROR")
        
        return registros
    
    def limpiar_formulario(self):
        """Limpia el formulario"""
        try:
            botones = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in botones:
                if "limpiar" in btn.text.lower():
                    btn.click()
                    time.sleep(2)
                    return True
            
            self.driver.get(self.url)
            time.sleep(4)
            return True
        except:
            pass
    
    def procesar_dnis(self, archivo: str):
        """Procesa lista de DNIs"""
        dnis = self._leer_dnis(archivo)
        if not dnis:
            self._log("No se encontraron DNIs", "ERROR")
            return
        
        self.stats["total"] = len(dnis)
        
        print("\n" + "="*70)
        print("SUNEDU BOT - MICROSOFT EDGE")
        print(f"Total DNIs: {len(dnis)}")
        print("="*70)
        print("\nIMPORTANTE:")
        print("- Se abrira Microsoft Edge")
        print("- TU ingresas el DNI y resuelves el CAPTCHA")
        print("- El bot extrae los datos automaticamente")
        print("="*70)
        
        input("\n[ENTER] Presiona ENTER para iniciar Edge...")
        
        if not self.iniciar_navegador():
            return
        
        try:
            for i, dni in enumerate(dnis, 1):
                print("\n" + "="*70)
                print(f"[{i}/{len(dnis)}] DNI: {dni}")
                print("="*70)
                
                if i == 1 or not self._verificar_pagina():
                    if not self.navegar():
                        continue
                else:
                    self.limpiar_formulario()
                
                # Modo manual
                registros = self.modo_manual(dni)
                self.resultados.extend(registros)
                
                if registros and registros[0].estado == "ENCONTRADO":
                    self.stats["exitosos"] += 1
                else:
                    self.stats["no_encontrados"] += 1
                
                # Guardar progreso
                if i % 5 == 0:
                    self._guardar_resultados(f"_progreso_{i}")
                
                # Preguntar continuar
                if i < len(dnis):
                    respuesta = input("\n[?] Continuar? (s/n): ").strip().lower()
                    if respuesta != 's':
                        break
        
        except KeyboardInterrupt:
            self._log("Interrumpido", "WARNING")
        
        except Exception as e:
            self._log(f"Error: {e}", "ERROR")
        
        finally:
            self.cerrar_navegador()
            self._guardar_resultados("_final")
            self._mostrar_estadisticas()
    
    def _verificar_pagina(self) -> bool:
        """Verifica si la página está cargada"""
        try:
            return "sunedu" in self.driver.current_url
        except:
            return False
    
    def _leer_dnis(self, archivo: str) -> List[str]:
        """Lee DNIs desde archivo"""
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
                if col.upper() in ['DNI', 'DOCUMENTO', 'NUMERO']:
                    dnis = df[col].dropna().astype(str).str.strip().tolist()
                    break
            
            dnis = [d for d in dnis if d.isdigit()]
            dnis = list(dict.fromkeys(dnis))
            
        except Exception as e:
            self._log(f"Error leyendo archivo: {e}", "ERROR")
        
        return dnis
    
    def _guardar_resultados(self, sufijo: str = ""):
        """Guarda resultados"""
        if not self.resultados:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        datos = [asdict(r) for r in self.resultados]
        df = pd.DataFrame(datos)
        
        excel_path = self.output_dir / f"SUNEDU_EDGE{sufijo}_{timestamp}.xlsx"
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
        csv_path = self.output_dir / f"SUNEDU_EDGE{sufijo}_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        txt_path = self.output_dir / f"SUNEDU_EDGE{sufijo}_{timestamp}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("SUNEDU - RESULTADOS (Microsoft Edge)\n")
            f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            for r in self.resultados:
                f.write(f"DNI: {r.dni}\n")
                f.write(f"Nombres: {r.nombres or 'NO ENCONTRADO'}\n")
                f.write(f"Grado/Titulo: {r.grado_o_titulo or 'N/A'}\n")
                f.write(f"Institucion: {r.institucion or 'N/A'}\n")
                f.write(f"Fecha Diploma: {r.fecha_diploma or 'N/A'}\n")
                f.write(f"Estado: {r.estado}\n")
                f.write("-"*80 + "\n")
        
        self._log(f"Guardado: {excel_path.name}")
    
    def _mostrar_estadisticas(self):
        """Muestra estadísticas"""
        print("\n" + "="*70)
        print("ESTADISTICAS")
        print("="*70)
        print(f"Total: {self.stats['total']}")
        print(f"Exitosos: {self.stats['exitosos']}")
        print(f"No encontrados: {self.stats['no_encontrados']}")
        print(f"Errores: {self.stats['errores']}")
        print("="*70)


def main():
    import sys
    
    print("="*70)
    print("  SUNEDU BOT - MICROSOFT EDGE")
    print("="*70)
    print("\nUsando Edge para evadir deteccion de Cloudflare")
    print("="*70)
    
    archivo = sys.argv[1] if len(sys.argv) > 1 else "dni_lista.csv"
    
    bot = SuneduEdgeBot()
    bot.procesar_dnis(archivo)
    
    print("\n[OK] PROCESO FINALIZADO")


if __name__ == "__main__":
    main()

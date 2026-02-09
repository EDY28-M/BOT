#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUNEDU BOT v2 - Versión Ultra Anti-Detección
Con soporte para modo manual (tú ingresas DNI y resuelves CAPTCHA)
y el bot extrae automáticamente los resultados.
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
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


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


class SuneduBotV2:
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
        """Inicia Chrome con máxima protección anti-detección"""
        self._log("Iniciando navegador en modo sigiloso...")
        
        try:
            options = uc.ChromeOptions()
            
            # === OPCIONES ANTI-DETECCIÓN AGRESIVAS ===
            options.add_argument("--no-first-run")
            options.add_argument("--no-service-autorun")
            options.add_argument("--password-store=basic")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-images")
            options.add_argument("--disable-javascript")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            
            # Ocultar WebDriver
            options.add_argument("--disable-webgl")
            options.add_argument("--disable-3d-apis")
            options.add_argument("--disable-webrtc")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            
            # User agent fijo común
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Idioma y zona horaria
            options.add_argument("--lang=es-PE")
            options.add_argument("--timezone=America/Lima")
            
            # Ventana
            options.add_argument("--window-size=1366,768")
            options.add_argument("--start-maximized")
            
            # Iniciar
            self.driver = uc.Chrome(options=options, version_main=144)
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 20)
            
            # Ejecutar scripts para ocultar Selenium
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['es-PE', 'es', 'en-US', 'en']});
                window.chrome = { runtime: {} };
            """)
            
            self._log("[OK] Navegador iniciado en modo sigiloso")
            
        except Exception as e:
            self._log(f"Error: {e}", "ERROR")
            raise
    
    def navegar(self):
        """Navega a la página"""
        try:
            self._log(f"Navegando a SUNEDU...")
            self.driver.get(self.url)
            time.sleep(5)  # Esperar carga completa
            self._log("[OK] Página cargada")
            return True
        except Exception as e:
            self._log(f"Error navegando: {e}", "ERROR")
            return False
    
    def esperar_manual(self, dni: str) -> bool:
        """Espera a que el usuario complete manualmente"""
        print("\n" + "="*70)
        print(f"MODO MANUAL - DNI: {dni}")
        print("="*70)
        print("""
[INSTRUCCIONES]:
  1. En la ventana de Chrome, ingresa el DNI manualmente
  2. Resuelve el CAPTCHA (marca "No soy un robot")
  3. Haz clic en "Buscar"
  4. Espera a que aparezcan los resultados
  5. Vuelve aquí y presiona ENTER
""")
        print("="*70)
        
        try:
            input("\n[ENTER] Presiona ENTER cuando veas los resultados... ")
            time.sleep(2)
            return True
        except:
            return False
    
    def extraer_datos(self, dni: str) -> List[RegistroProfesional]:
        """Extrae datos de la tabla de resultados"""
        registros = []
        
        try:
            # Tomar screenshot
            self.driver.save_screenshot(str(self.screenshots_dir / f"{dni}_resultado.png"))
            
            # Esperar tabla
            time.sleep(3)
            
            # Buscar filas de resultados
            filas = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr, .tabla-resultados tbody tr, tr.ng-star-inserted")
            
            if not filas:
                # Verificar si no hay resultados
                page_text = self.driver.page_source.lower()
                if any(x in page_text for x in ["no se encontraron", "sin resultados", "no existe"]):
                    self._log("No se encontraron registros")
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
                    
                    # Extraer datos
                    nombres = celdas[0].text.strip().split('\n')[0] if len(celdas) > 0 else ""
                    
                    # Celda de grado/título (generalmente la segunda)
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
                    
                    # Institución
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
                    self._log(f"  Error en fila {i}: {e}", "WARNING")
                    continue
            
        except Exception as e:
            self._log(f"Error extrayendo: {e}", "ERROR")
        
        return registros
    
    def limpiar_formulario(self):
        """Limpia el formulario para siguiente consulta"""
        try:
            # Buscar botón limpiar
            botones = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in botones:
                if "limpiar" in btn.text.lower() or "limpiar" in btn.get_attribute("class").lower():
                    btn.click()
                    time.sleep(2)
                    return True
            
            # Si no hay botón limpiar, recargar página
            self.driver.get(self.url)
            time.sleep(4)
            return True
            
        except:
            # Recargar como fallback
            try:
                self.driver.get(self.url)
                time.sleep(4)
            except:
                pass
    
    def procesar_dnis(self, archivo: str):
        """Procesa lista de DNIs en modo manual"""
        # Leer DNIs
        dnis = self._leer_dnis(archivo)
        if not dnis:
            self._log("No se encontraron DNIs", "ERROR")
            return
        
        self.stats["total"] = len(dnis)
        
        print("\n" + "="*70)
        print(f"SUNEDU BOT v2 - MODO MANUAL")
        print(f"Total DNIs a procesar: {len(dnis)}")
        print("="*70)
        print("\nIMPORTANTE:")
        print("- El navegador se abrirá automaticamente")
        print("- TU debes ingresar el DNI y resolver el CAPTCHA")
        print("- El bot extraera los datos automaticamente")
        print("- Presiona Ctrl+C para salir en cualquier momento")
        print("="*70)
        
        input("\n[ENTER] Presiona ENTER para iniciar...")
        
        # Iniciar navegador
        self.iniciar_navegador()
        
        try:
            for i, dni in enumerate(dnis, 1):
                print("\n" + "="*70)
                print(f"[{i}/{len(dnis)}] DNI: {dni}")
                print("="*70)
                
                # Navegar (solo la primera vez o si es necesario)
                if i == 1 or not self._verificar_pagina_cargada():
                    if not self.navegar():
                        continue
                else:
                    self.limpiar_formulario()
                
                # Esperar que usuario complete manualmente
                if not self.esperar_manual(dni):
                    break
                
                # Extraer datos
                registros = self.extraer_datos(dni)
                self.resultados.extend(registros)
                
                if registros and registros[0].estado == "ENCONTRADO":
                    self.stats["exitosos"] += 1
                else:
                    self.stats["no_encontrados"] += 1
                
                # Guardar progreso
                if i % 5 == 0:
                    self._guardar_resultados(f"_progreso_{i}")
                
                # Preguntar si continuar
                if i < len(dnis):
                    respuesta = input("\n[?] Continuar con siguiente DNI? (s/n): ").strip().lower()
                    if respuesta != 's':
                        break
        
        except KeyboardInterrupt:
            self._log("Interrumpido por usuario", "WARNING")
        
        except Exception as e:
            self._log(f"Error: {e}", "ERROR")
        
        finally:
            # Cerrar navegador
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            
            # Guardar resultados
            self._guardar_resultados("_final")
            self._mostrar_estadisticas()
    
    def _verificar_pagina_cargada(self) -> bool:
        """Verifica si la página sigue cargada"""
        try:
            current_url = self.driver.current_url
            return "sunedu" in current_url
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
        
        # Excel
        excel_path = self.output_dir / f"SUNEDU{sufijo}_{timestamp}.xlsx"
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
        # CSV
        csv_path = self.output_dir / f"SUNEDU{sufijo}_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        # TXT
        txt_path = self.output_dir / f"SUNEDU{sufijo}_{timestamp}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("SUNEDU - RESULTADOS\n")
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
    print("  SUNEDU BOT v2 - MODO MANUAL (Anti-Deteccion)")
    print("="*70)
    print("\nEste modo abre el navegador y TU ingresas:")
    print("  1. El DNI en el campo correspondiente")
    print("  2. Resuelves el CAPTCHA manualmente")
    print("  3. Haces clic en 'Buscar'")
    print("  4. El bot extrae los datos automaticamente")
    print("="*70)
    
    archivo = sys.argv[1] if len(sys.argv) > 1 else "dni_lista.csv"
    
    bot = SuneduBotV2()
    bot.procesar_dnis(archivo)
    
    print("\n[OK] PROCESO FINALIZADO")


if __name__ == "__main__":
    main()

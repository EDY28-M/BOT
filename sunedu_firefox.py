#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUNEDU BOT - Versión Firefox
Usa Firefox en lugar de Chrome/Edge
"""

import os
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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


class SuneduFirefoxBot:
    def __init__(self):
        self.resultados: List[RegistroProfesional] = []
        self.driver = None
        self.wait = None
        
        self.url = "https://constanciasweb.sunedu.gob.pe/#/modulos/grados-y-titulos"
        
        self.output_dir = Path("resultados")
        self.output_dir.mkdir(exist_ok=True)
        self.screenshots_dir = Path("screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
        
        self.stats = {"total": 0, "exitosos": 0, "no_encontrados": 0, "errores": 0}
    
    def _log(self, mensaje: str, tipo: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{tipo}] {mensaje}")
    
    def iniciar_navegador(self):
        """Inicia Firefox"""
        self._log("Iniciando Firefox...")
        
        try:
            options = FirefoxOptions()
            
            # Opciones básicas
            options.add_argument("--width=1366")
            options.add_argument("--height=768")
            
            # User agent
            options.set_preference("general.useragent.override", 
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0")
            
            # Deshabilitar notificaciones de automatización
            options.set_preference("dom.webdriver.enabled", False)
            options.set_preference("useAutomationExtension", False)
            
            # Iniciar Firefox
            self.driver = webdriver.Firefox(options=options)
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 20)
            
            self._log("[OK] Firefox iniciado")
            return True
            
        except Exception as e:
            self._log(f"Error: {e}", "ERROR")
            self._log("Asegurate de tener Firefox instalado", "WARNING")
            self._log("Descarga Firefox desde: https://firefox.com", "INFO")
            return False
    
    def cerrar_navegador(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def navegar(self):
        try:
            self._log("Navegando a SUNEDU...")
            self.driver.get(self.url)
            time.sleep(5)
            return True
        except Exception as e:
            self._log(f"Error: {e}", "ERROR")
            return False
    
    def modo_manual(self, dni: str) -> List[RegistroProfesional]:
        registros = []
        
        print("\n" + "="*70)
        print(f"DNI: {dni}")
        print("="*70)
        print("""
[INSTRUCCIONES]:
  1. En Firefox, ingresa el DNI manualmente
  2. Resuelve el CAPTCHA
  3. Haz clic en "Buscar"
  4. Espera los resultados
  5. Presiona ENTER aqui
""")
        
        try:
            input("\n[ENTER] Presiona ENTER cuando veas los resultados: ")
            time.sleep(2)
            registros = self.extraer_datos(dni)
        except KeyboardInterrupt:
            pass
        
        return registros
    
    def extraer_datos(self, dni: str) -> List[RegistroProfesional]:
        registros = []
        
        try:
            self.driver.save_screenshot(str(self.screenshots_dir / f"{dni}.png"))
            time.sleep(2)
            
            filas = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr, tr.ng-star-inserted")
            
            if not filas:
                page_text = self.driver.page_source.lower()
                if any(x in page_text for x in ["no se encontraron", "sin resultados"]):
                    registros.append(RegistroProfesional(
                        dni=dni,
                        estado="NO ENCONTRADO",
                        fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                    return registros
            
            for fila in filas:
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
                    self._log(f"  [OK] {grado_titulo[:50]}...")
                    
                except:
                    continue
            
        except Exception as e:
            self._log(f"Error: {e}", "ERROR")
        
        return registros
    
    def limpiar_formulario(self):
        try:
            self.driver.get(self.url)
            time.sleep(4)
        except:
            pass
    
    def procesar_dnis(self, archivo: str):
        dnis = self._leer_dnis(archivo)
        if not dnis:
            print("[!] No se encontraron DNIs")
            return
        
        self.stats["total"] = len(dnis)
        
        print("\n" + "="*70)
        print("SUNEDU BOT - FIREFOX")
        print(f"Total DNIs: {len(dnis)}")
        print("="*70)
        
        input("\n[ENTER] Presiona ENTER para iniciar Firefox...")
        
        if not self.iniciar_navegador():
            return
        
        try:
            for i, dni in enumerate(dnis, 1):
                print("\n" + "="*70)
                print(f"[{i}/{len(dnis)}] DNI: {dni}")
                print("="*70)
                
                if i == 1:
                    if not self.navegar():
                        continue
                else:
                    self.limpiar_formulario()
                
                registros = self.modo_manual(dni)
                self.resultados.extend(registros)
                
                if registros and registros[0].estado == "ENCONTRADO":
                    self.stats["exitosos"] += 1
                else:
                    self.stats["no_encontrados"] += 1
                
                if i % 5 == 0:
                    self._guardar_resultados(f"_progreso_{i}")
                
                if i < len(dnis):
                    respuesta = input("\n[?] Continuar? (s/n): ").strip().lower()
                    if respuesta != 's':
                        break
        
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self._log(f"Error: {e}", "ERROR")
        finally:
            self.cerrar_navegador()
            self._guardar_resultados("_final")
            self._mostrar_estadisticas()
    
    def _leer_dnis(self, archivo: str) -> List[str]:
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
            self._log(f"Error: {e}", "ERROR")
        
        return dnis
    
    def _guardar_resultados(self, sufijo: str = ""):
        if not self.resultados:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        datos = [asdict(r) for r in self.resultados]
        df = pd.DataFrame(datos)
        
        excel_path = self.output_dir / f"SUNEDU_FIREFOX{sufijo}_{timestamp}.xlsx"
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
        csv_path = self.output_dir / f"SUNEDU_FIREFOX{sufijo}_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        self._log(f"Guardado: {excel_path.name}")
    
    def _mostrar_estadisticas(self):
        print("\n" + "="*70)
        print("ESTADISTICAS")
        print("="*70)
        print(f"Total: {self.stats['total']}")
        print(f"Exitosos: {self.stats['exitosos']}")
        print(f"No encontrados: {self.stats['no_encontrados']}")
        print("="*70)


def main():
    import sys
    
    print("="*70)
    print("  SUNEDU BOT - FIREFOX")
    print("="*70)
    
    archivo = sys.argv[1] if len(sys.argv) > 1 else "dni_lista.csv"
    
    bot = SuneduFirefoxBot()
    bot.procesar_dnis(archivo)
    
    print("\n[OK] PROCESO FINALIZADO")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUNEDU Scraper con Selenium - Alternativa si Playwright no está disponible
"""

import json
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


@dataclass
class RegistroProfesional:
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


class SuneduScraperSelenium:
    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.resultados: List[RegistroProfesional] = []
        self.url = self.config.get("url", "https://constanciasweb.sunedu.gob.pe/#/modulos/grados-y-titulos")
        self.timeout_captcha = self.config.get("timeout_captcha", 120)
        self.delay = self.config.get("delay_entre_consultas", 3)
        self.headless = self.config.get("headless", False)
        
        self.output_dir = Path("resultados")
        self.output_dir.mkdir(exist_ok=True)
        self.screenshots_dir = Path("screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
    
    def iniciar_navegador(self):
        """Inicia Chrome con Selenium"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        # Deshabilitar detección de automation
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 30)
    
    def cerrar_navegador(self):
        if hasattr(self, 'driver'):
            self.driver.quit()
    
    def esperar_captcha_manual(self, dni: str) -> bool:
        print(f"\n{'='*60}")
        print(f"DNI: {dni}")
        print(f"{'='*60}")
        print("\n⚠️  Completa el CAPTCHA y presiona ENTER...")
        
        try:
            input("👉 Presiona ENTER cuando termines... ")
            time.sleep(2)
            return True
        except:
            return False
    
    def consultar_dni(self, dni: str) -> List[RegistroProfesional]:
        registros = []
        
        try:
            print(f"\n🌐 Consultando DNI: {dni}")
            self.driver.get(self.url)
            time.sleep(3)
            
            # Buscar campo DNI
            try:
                campo_dni = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
                )
            except:
                # Intentar otros selectores
                selectores = ["input", "input.form-control", "input.p-inputtext"]
                for sel in selectores:
                    try:
                        campo_dni = self.driver.find_element(By.CSS_SELECTOR, sel)
                        break
                    except:
                        continue
            
            campo_dni.clear()
            campo_dni.send_keys(dni)
            print(f"   ✏️  DNI ingresado")
            
            # Buscar y hacer clic en botón
            try:
                boton = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Buscar') or contains(text(), 'Consultar')]")
                boton.click()
            except:
                campo_dni.send_keys(Keys.ENTER)
            
            time.sleep(3)
            
            # Verificar CAPTCHA
            if self.detectar_captcha():
                print("   🔒 CAPTCHA detectado - Resuelve manualmente")
                self.driver.save_screenshot(str(self.screenshots_dir / f"{dni}_captcha.png"))
                if not self.esperar_captcha_manual(dni):
                    return []
            
            # Esperar y extraer resultados
            time.sleep(3)
            registros = self.extraer_datos(dni)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        return registros
    
    def detectar_captcha(self) -> bool:
        indicadores = [".g-recaptcha", "[data-sitekey]", "iframe[src*='recaptcha']", ".h-captcha", "#captcha"]
        for ind in indicadores:
            try:
                elem = self.driver.find_element(By.CSS_SELECTOR, ind)
                if elem.is_displayed():
                    return True
            except:
                continue
        return False
    
    def extraer_datos(self, dni: str) -> List[RegistroProfesional]:
        registros = []
        
        try:
            # Esperar tabla
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.custom-table")))
            
            filas = self.driver.find_elements(By.CSS_SELECTOR, "table.custom-table tbody tr.ng-star-inserted")
            print(f"   📊 {len(filas)} registro(s) encontrado(s)")
            
            for fila in filas:
                try:
                    celdas = fila.find_elements(By.TAG_NAME, "td")
                    if len(celdas) < 3:
                        continue
                    
                    # Extraer datos
                    nombres = celdas[0].text.strip().split('\n')[0]
                    
                    # Grado/Título
                    titulo_elem = celdas[1].find_element(By.CSS_SELECTOR, "p.poppins-bold")
                    grado_titulo = titulo_elem.text.strip() if titulo_elem else ""
                    
                    # Fechas
                    fechas = celdas[1].find_elements(By.TAG_NAME, "p")
                    fecha_diploma = ""
                    fecha_matricula = "Sin información"
                    fecha_egreso = "Sin información"
                    
                    for f in fechas:
                        texto = f.text
                        if "Fecha de diploma:" in texto:
                            fecha_diploma = texto.replace("Fecha de diploma:", "").strip()
                        elif "Fecha matrícula:" in texto:
                            fecha_matricula = texto.replace("Fecha matrícula:", "").strip()
                        elif "Fecha egreso:" in texto:
                            fecha_egreso = texto.replace("Fecha egreso:", "").strip()
                    
                    # Institución
                    inst_elem = celdas[2].find_element(By.CSS_SELECTOR, "p.font-bold")
                    institucion = inst_elem.text.strip() if inst_elem else ""
                    
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
                    print(f"   ✅ {grado_titulo}")
                    
                except Exception as e:
                    continue
                    
        except TimeoutException:
            print(f"   ⚠️  No se encontraron registros")
            registros.append(RegistroProfesional(
                dni=dni, nombres="", grado_o_titulo="", institucion="",
                fecha_diploma="", fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                estado="NO ENCONTRADO"
            ))
        
        return registros
    
    def procesar_lista(self, archivo: str):
        dnis = self.leer_dnis(archivo)
        print(f"\n📋 Total DNIs: {len(dnis)}")
        
        self.iniciar_navegador()
        
        try:
            for i, dni in enumerate(dnis, 1):
                print(f"\n{'─'*60}")
                print(f"{i}/{len(dnis)}: {dni}")
                
                registros = self.consultar_dni(dni)
                self.resultados.extend(registros)
                
                if i % 5 == 0:
                    self.guardar_resultados("_parcial")
                
                if i < len(dnis):
                    time.sleep(self.delay)
        finally:
            self.cerrar_navegador()
            self.guardar_resultados()
    
    def leer_dnis(self, archivo: str) -> List[str]:
        dnis = []
        path = Path(archivo)
        
        if not path.exists():
            return []
        
        try:
            if archivo.endswith('.xlsx') or archivo.endswith('.xls'):
                df = pd.read_excel(archivo)
            else:
                df = pd.read_csv(archivo)
            
            for col in df.columns:
                if col.upper() == 'DNI':
                    dnis = df[col].dropna().astype(str).str.strip().tolist()
                    break
            
            dnis = [d for d in dnis if d.isdigit()]
            dnis = list(dict.fromkeys(dnis))
        except Exception as e:
            print(f"Error leyendo archivo: {e}")
        
        return dnis
    
    def guardar_resultados(self, sufijo: str = ""):
        if not self.resultados:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        datos = [asdict(r) for r in self.resultados]
        df = pd.DataFrame(datos)
        
        excel_path = self.output_dir / f"resultados_sunedu{sufijo}_{timestamp}.xlsx"
        csv_path = self.output_dir / f"resultados_sunedu{sufijo}_{timestamp}.csv"
        
        df.to_excel(excel_path, index=False, engine='openpyxl')
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        print(f"\n💾 Guardado: {excel_path}")


def main():
    print("="*70)
    print("     SUNEDU SCRAPER - Versión Selenium")
    print("="*70)
    
    import sys
    archivo = sys.argv[1] if len(sys.argv) > 1 else "dni_lista.csv"
    
    scraper = SuneduScraperSelenium()
    scraper.procesar_lista(archivo)
    
    print("\n" + "="*70)
    print("                    FINALIZADO")
    print("="*70)


if __name__ == "__main__":
    main()

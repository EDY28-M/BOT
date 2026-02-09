"""
SUNEDU Bot - Automatización de consultas de grados y títulos
"""

import os
import sys
import subprocess
import json
import time
import random
import pandas as pd
import winreg
import re
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import undetected_chromedriver as uc
from fake_useragent import UserAgent


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
    observaciones: str = ""


class SuneduBot:
    """Bot para automatizar consultas en SUNEDU"""
    
    # URLs
    url_principal = "https://enlinea.sunedu.gob.pe/verificainscripcion"
    url_consulta = "https://constanciasweb.sunedu.gob.pe/#/modulos/grados-y-titulos"
    
    # Configuración por defecto
    defaults = {
        "delay_min": 5,
        "delay_max": 12,
        "timeout_captcha": 180,
        "timeout_pagina": 30,
        "headless": False,
        "guardar_screenshots": True,
        "modo_captcha": "manual",
        "reintentos": 2,
        "guardar_cada": 5
    }
    
    def __init__(self, config_file: str = "config.json"):
        """Inicializa el bot cargando configuración y directorios"""
        self.config_file = config_file
        self.logger = []  # Inicializar logger PRIMERO
        self.dirs = {
            "output": Path("output"),
            "screenshots": Path("screenshots"),
            "logs": Path("logs"),
            "data": Path("data")
        }
        self.config = self._cargar_config()
        self.driver: Optional[uc.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.ua = UserAgent()
        self.resultados: List[RegistroProfesional] = []
        
        # Crear directorios necesarios
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
        
        self._log("=" * 60)
        self._log("SUNEDU Bot Iniciado")
        self._log(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._log("=" * 60)
    
    def _cargar_config(self) -> Dict:
        """Carga configuración desde archivo JSON con valores por defecto"""
        config = self.defaults.copy()
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config.update(json.load(f))
                self._log(f"✓ Configuración cargada desde {self.config_file}")
            except Exception as e:
                self._log(f"⚠ Error cargando config: {e}. Usando defaults.")
        else:
            # Crear archivo de configuración por defecto
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.defaults, f, indent=4)
                self._log(f"✓ Archivo de configuración creado: {self.config_file}")
            except Exception as e:
                self._log(f"⚠ Error creando config: {e}")
        
        return config
    
    def _log(self, mensaje: str, nivel: str = "INFO"):
        """Guarda logs en archivo y consola"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linea_log = f"[{timestamp}] [{nivel}] {mensaje}"
        
        print(linea_log)
        self.logger.append(linea_log)
        
        # Guardar en archivo
        log_file = self.dirs["logs"] / f"sunedu_{datetime.now().strftime('%Y%m%d')}.log"
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(linea_log + "\n")
        except:
            pass
    
    def _random_delay(self, min_seg: int = None, max_seg: int = None):
        """Espera aleatoria entre min y max segundos"""
        min_seg = min_seg or self.config["delay_min"]
        max_seg = max_seg or self.config["delay_max"]
        tiempo = random.uniform(min_seg, max_seg)
        self._log(f"⏱ Esperando {tiempo:.1f} segundos...")
        time.sleep(tiempo)
    
    def _matar_procesos_chrome(self):
        """Mata procesos de Chrome y ChromeDriver colgados"""
        procesos = ["chrome.exe", "chromedriver.exe"]
        for proceso in procesos:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", proceso],
                    capture_output=True,
                    check=False
                )
            except:
                pass
    
    def _obtener_version_chrome(self) -> Optional[str]:
        """Detecta versión de Chrome desde el registro de Windows"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Google\Chrome\BLBeacon"
            )
            version, _ = winreg.QueryValueEx(key, "version")
            winreg.CloseKey(key)
            return version
        except:
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"Software\Google\Chrome\BLBeacon"
                )
                version, _ = winreg.QueryValueEx(key, "version")
                winreg.CloseKey(key)
                return version
            except:
                return None
    
    def iniciar_navegador(self) -> bool:
        """Inicia Chrome con undetected-chromedriver"""
        try:
            self._matar_procesos_chrome()
            self._random_delay(1, 2)
            
            self._log("🚀 Iniciando navegador Chrome...")
            
            chrome_version = self._obtener_version_chrome()
            if chrome_version:
                self._log(f"✓ Versión de Chrome detectada: {chrome_version}")
            
            options = uc.ChromeOptions()
            
            # User agent aleatorio
            user_agent = self.ua.random
            options.add_argument(f"--user-agent={user_agent}")
            
            # Opciones adicionales
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            options.add_argument("--disable-site-isolation-trials")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            # Window size
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--start-maximized")
            
            # Headless mode
            if self.config["headless"]:
                options.add_argument("--headless=new")
            
            # Crear driver
            if chrome_version:
                try:
                    self.driver = uc.Chrome(options=options, version_main=int(chrome_version.split('.')[0]))
                except:
                    self.driver = uc.Chrome(options=options)
            else:
                self.driver = uc.Chrome(options=options)
            
            # Configurar timeouts
            self.driver.set_page_load_timeout(self.config["timeout_pagina"])
            self.wait = WebDriverWait(self.driver, self.config["timeout_pagina"])
            
            self._log("✓ Navegador iniciado correctamente")
            return True
            
        except Exception as e:
            self._log(f"✗ Error iniciando navegador: {e}", "ERROR")
            return False
    
    def cerrar_navegador(self):
        """Cierra el navegador y limpia recursos"""
        if self.driver:
            try:
                self.driver.quit()
                self._log("✓ Navegador cerrado")
            except Exception as e:
                self._log(f"⚠ Error cerrando navegador: {e}")
            finally:
                self.driver = None
                self.wait = None
        
        self._matar_procesos_chrome()
    
    def _detectar_captcha(self) -> bool:
        """Detecta si hay un CAPTCHA en la página"""
        if not self.driver:
            return False
        
        indicadores_captcha = [
            "captcha",
            "recaptcha",
            "g-recaptcha",
            "h-captcha",
            "cf-turnstile",
            "human verification",
            "verify you are human",
            "soy humano",
            "no soy un robot",
            "reto de seguridad"
        ]
        
        try:
            page_source = self.driver.page_source.lower()
            for indicador in indicadores_captcha:
                if indicador in page_source:
                    return True
            
            # Buscar elementos iframe comunes de captcha
            captcha_selectors = [
                "iframe[src*='recaptcha']",
                "iframe[src*='captcha']",
                ".g-recaptcha",
                "#g-recaptcha",
                "[data-sitekey]"
            ]
            
            for selector in captcha_selectors:
                try:
                    elementos = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elementos:
                        return True
                except:
                    pass
                    
        except Exception as e:
            self._log(f"⚠ Error detectando CAPTCHA: {e}")
        
        return False
    
    def _esperar_captcha_manual(self) -> bool:
        """Pausa para que el usuario resuelva el CAPTCHA manualmente"""
        if not self._detectar_captcha():
            return True
        
        if self.config["modo_captcha"] == "manual":
            self._log("=" * 60)
            self._log("🚨 CAPTCHA DETECTADO")
            self._log("Por favor resuelva el CAPTCHA manualmente en el navegador")
            self._log(f"Tiempo máximo de espera: {self.config['timeout_captcha']} segundos")
            self._log("=" * 60)
            
            self._tomar_screenshot("captcha_detectado")
            
            # Esperar hasta que el captcha desaparezca o timeout
            tiempo_inicio = time.time()
            while time.time() - tiempo_inicio < self.config["timeout_captcha"]:
                time.sleep(2)
                if not self._detectar_captcha():
                    self._log("✓ CAPTCHA resuelto")
                    return True
                
                tiempo_restante = int(self.config["timeout_captcha"] - (time.time() - tiempo_inicio))
                if tiempo_restante % 10 == 0:
                    self._log(f"⏱ Esperando... {tiempo_restante}s restantes")
            
            self._log("✗ Timeout esperando CAPTCHA", "ERROR")
            return False
        
        return False
    
    def _tomar_screenshot(self, nombre: str) -> str:
        """Guarda una captura de pantalla"""
        if not self.driver or not self.config["guardar_screenshots"]:
            return ""
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{nombre}_{timestamp}.png"
            filepath = self.dirs["screenshots"] / filename
            
            self.driver.save_screenshot(str(filepath))
            self._log(f"📸 Screenshot guardado: {filepath}")
            return str(filepath)
        except Exception as e:
            self._log(f"⚠ Error guardando screenshot: {e}")
            return ""
    
    def _navegar_a_consulta(self) -> bool:
        """Navega a la URL de consulta de SUNEDU"""
        try:
            self._log(f"🌐 Navegando a: {self.url_consulta}")
            self.driver.get(self.url_consulta)
            self._random_delay(3, 5)
            
            # Verificar si hay captcha
            if self._detectar_captcha():
                if not self._esperar_captcha_manual():
                    return False
            
            self._tomar_screenshot("pagina_cargada")
            return True
            
        except Exception as e:
            self._log(f"✗ Error navegando: {e}", "ERROR")
            return False
    
    def _ingresar_dni(self, dni: str) -> bool:
        """Ingresa el DNI en el formulario"""
        try:
            self._log(f"📝 Ingresando DNI: {dni}")
            
            # Buscar campo DNI con múltiples selectores
            selectores_dni = [
                "input[placeholder*='DNI' i]",
                "input[name*='dni' i]",
                "input[id*='dni' i]",
                "input[type='number']",
                "input[type='text']",
                "input.form-control",
                "input"
            ]
            
            campo_dni = None
            for selector in selectores_dni:
                try:
                    elementos = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elementos:
                        if elem.is_displayed():
                            campo_dni = elem
                            break
                    if campo_dni:
                        break
                except:
                    continue
            
            if not campo_dni:
                self._log("✗ No se encontró campo DNI", "ERROR")
                return False
            
            # Limpiar y llenar campo
            campo_dni.clear()
            self._random_delay(0.5, 1)
            campo_dni.send_keys(dni)
            self._random_delay(0.5, 1)
            
            self._log("✓ DNI ingresado")
            return True
            
        except Exception as e:
            self._log(f"✗ Error ingresando DNI: {e}", "ERROR")
            return False
    
    def _hacer_click_buscar(self) -> bool:
        """Hace clic en el botón de búsqueda"""
        try:
            self._log("🔍 Buscando botón de consulta...")
            
            selectores_boton = [
                "button[type='submit']",
                "button.btn-primary",
                "button.btn-buscar",
                "button:contains('Buscar')",
                "button:contains('Consultar')",
                "input[type='submit']",
                "button i.fa-search",
                "button .glyphicon-search",
                "button"
            ]
            
            boton = None
            for selector in selectores_boton:
                try:
                    if ":contains(" in selector:
                        # XPath para contains text
                        text = selector.split("'")[1]
                        elementos = self.driver.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
                    else:
                        elementos = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for elem in elementos:
                        if elem.is_displayed() and elem.is_enabled():
                            boton = elem
                            break
                    if boton:
                        break
                except:
                    continue
            
            if not boton:
                # Intentar con Enter
                self._log("⚠ Botón no encontrado, usando tecla Enter")
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                actions.send_keys(Keys.RETURN).perform()
            else:
                self._random_delay(0.5, 1)
                boton.click()
            
            self._log("✓ Búsqueda iniciada")
            self._random_delay(3, 5)
            return True
            
        except Exception as e:
            self._log(f"✗ Error haciendo click: {e}", "ERROR")
            return False
    
    def _extraer_resultados(self, dni: str) -> RegistroProfesional:
        """Extrae datos de la tabla de resultados de SUNEDU"""
        registro = RegistroProfesional(
            dni=dni,
            fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        try:
            self._log("🔍 Extrayendo datos de la tabla...")
            
            # Esperar a que cargue la tabla
            selectores_tabla = [
                "table.custom-table",
                "table tbody",
                ".tabla-resultados",
                "#resultados table",
                "table",
                ".table"
            ]
            
            tabla = None
            for selector in selectores_tabla:
                try:
                    tabla = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if tabla:
                        break
                except:
                    continue
            
            if not tabla:
                self._log("⚠ No se encontró tabla de resultados")
                registro.estado = "NO ENCONTRADO"
                registro.observaciones = "No se encontraron resultados para el DNI"
                return registro
            
            # Buscar filas de datos
            selectores_filas = [
                "tr.ng-star-inserted",
                "tr[data-row]",
                "tbody tr",
                "tr"
            ]
            
            filas = []
            for selector in selectores_filas:
                try:
                    filas = tabla.find_elements(By.CSS_SELECTOR, selector)
                    if len(filas) > 0:
                        break
                except:
                    continue
            
            if not filas:
                self._log("⚠ No se encontraron filas en la tabla")
                registro.estado = "NO ENCONTRADO"
                registro.observaciones = "Tabla vacía"
                return registro
            
            self._log(f"✓ Se encontraron {len(filas)} filas")
            
            # Procesar la primera fila con datos
            for fila in filas:
                try:
                    celdas = fila.find_elements(By.CSS_SELECTOR, "td")
                    if len(celdas) < 3:
                        continue
                    
                    # Celda 0: Nombres
                    texto_nombres = celdas[0].text.strip()
                    if texto_nombres:
                        # Buscar formato "APELLIDO, NOMBRE" o texto en mayúsculas
                        if re.match(r'^[A-ZÁÉÍÓÚÑ\s,]+$', texto_nombres):
                            registro.nombres = texto_nombres
                        else:
                            registro.nombres = texto_nombres.upper()
                    
                    # Celda 1: Grado/Título y fechas
                    texto_celda1 = celdas[1].text.strip()
                    if texto_celda1:
                        lineas = texto_celda1.split('\n')
                        
                        # Primera línea es el título
                        if lineas:
                            registro.grado_o_titulo = lineas[0].strip()
                        
                        # Buscar fechas en las líneas
                        for linea in lineas:
                            linea_lower = linea.lower()
                            
                            # Fecha de diploma
                            if "diploma:" in linea_lower or "fecha diploma" in linea_lower:
                                match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4})', linea)
                                if match:
                                    registro.fecha_diploma = match.group(1)
                            
                            # Fecha de matrícula
                            elif "matricula:" in linea_lower or "matrícula:" in linea_lower or "fecha matricula" in linea_lower:
                                match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4})', linea)
                                if match:
                                    registro.fecha_matricula = match.group(1)
                            
                            # Fecha de egreso
                            elif "egreso:" in linea_lower or "fecha egreso" in linea_lower:
                                match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4})', linea)
                                if match:
                                    registro.fecha_egreso = match.group(1)
                    
                    # Celda 2: Institución
                    texto_institucion = celdas[2].text.strip()
                    if texto_institucion:
                        # Buscar UNIVERSIDAD, INSTITUTO o texto en mayúsculas
                        if re.search(r'(UNIVERSIDAD|INSTITUTO|ESCUELA|CENTRO|ACADEMIA)', texto_institucion, re.IGNORECASE):
                            registro.institucion = texto_institucion
                        else:
                            registro.institucion = texto_institucion.upper()
                    
                    # Si encontramos datos válidos, marcar como éxito
                    if registro.nombres and registro.grado_o_titulo:
                        registro.estado = "ENCONTRADO"
                        registro.observaciones = "Registro encontrado exitosamente"
                        self._log(f"✓ Datos extraídos: {registro.nombres[:30]}... - {registro.grado_o_titulo[:30]}...")
                        break
                    
                except Exception as e:
                    self._log(f"⚠ Error procesando fila: {e}")
                    continue
            
            # Si no se encontraron datos
            if registro.estado == "PENDIENTE":
                registro.estado = "NO ENCONTRADO"
                registro.observaciones = "No se pudieron extraer datos de la tabla"
            
            return registro
            
        except Exception as e:
            self._log(f"✗ Error extrayendo resultados: {e}", "ERROR")
            registro.estado = "ERROR"
            registro.observaciones = f"Error: {str(e)}"
            return registro
    
    def consultar_dni(self, dni: str, reintentos: int = None) -> RegistroProfesional:
        """Consulta un DNI específico en SUNEDU"""
        reintentos = reintentos or self.config["reintentos"]
        
        self._log("=" * 60)
        self._log(f"🔍 Consultando DNI: {dni}")
        self._log("=" * 60)
        
        for intento in range(reintentos + 1):
            if intento > 0:
                self._log(f"🔄 Reintento {intento} de {reintentos}")
                self._random_delay(5, 8)
            
            try:
                # Navegar a la página
                if not self._navegar_a_consulta():
                    continue
                
                # Ingresar DNI
                if not self._ingresar_dni(dni):
                    continue
                
                # Hacer click en buscar
                if not self._hacer_click_buscar():
                    continue
                
                # Verificar captcha después de buscar
                if self._detectar_captcha():
                    if not self._esperar_captcha_manual():
                        continue
                    self._random_delay(2, 4)
                
                # Extraer resultados
                registro = self._extraer_resultados(dni)
                
                # Tomar screenshot del resultado
                self._tomar_screenshot(f"resultado_{dni}")
                
                return registro
                
            except Exception as e:
                self._log(f"✗ Error en intento {intento + 1}: {e}", "ERROR")
                self._tomar_screenshot(f"error_{dni}_intento{intento + 1}")
        
        # Si todos los intentos fallaron
        return RegistroProfesional(
            dni=dni,
            fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            estado="ERROR",
            observaciones=f"Fallaron todos los intentos ({reintentos + 1})"
        )
    
    def procesar_lista_dnis(self, archivo_dnis: str) -> List[RegistroProfesional]:
        """Procesa una lista de DNIs desde un archivo"""
        self._log(f"📁 Procesando archivo: {archivo_dnis}")
        
        # Leer DNIs
        dnis = self._leer_dnis(archivo_dnis)
        if not dnis:
            self._log("✗ No se pudieron leer DNIs del archivo", "ERROR")
            return []
        
        self._log(f"✓ Total de DNIs a procesar: {len(dnis)}")
        
        # Iniciar navegador
        if not self.iniciar_navegador():
            return []
        
        resultados = []
        guardar_cada = self.config.get("guardar_cada", 5)
        
        try:
            for i, dni in enumerate(dnis, 1):
                self._log(f"\n📊 Progreso: {i}/{len(dnis)} ({(i/len(dnis)*100):.1f}%)")
                
                # Consultar DNI
                registro = self.consultar_dni(dni)
                resultados.append(registro)
                self.resultados.append(registro)
                
                # Guardar resultados parciales
                if i % guardar_cada == 0 or i == len(dnis):
                    self._guardar_resultados(resultados, suffix=f"_parcial_{i}")
                
                # Delay entre consultas
                if i < len(dnis):
                    self._random_delay()
                    
        except KeyboardInterrupt:
            self._log("\n⚠ Proceso interrumpido por el usuario", "WARNING")
        except Exception as e:
            self._log(f"✗ Error en procesamiento: {e}", "ERROR")
        finally:
            # Guardar resultados finales
            self._guardar_resultados(resultados, suffix="_final")
            self.cerrar_navegador()
            self._mostrar_estadisticas()
        
        return resultados
    
    def _leer_dnis(self, archivo: str) -> List[str]:
        """Lee DNIs desde un archivo CSV o Excel"""
        dnis = []
        ruta = Path(archivo)
        
        if not ruta.exists():
            # Buscar en directorio data
            ruta = self.dirs["data"] / archivo
        
        if not ruta.exists():
            self._log(f"✗ Archivo no encontrado: {archivo}")
            return []
        
        try:
            extension = ruta.suffix.lower()
            
            if extension == '.csv':
                df = pd.read_csv(ruta, dtype=str)
            elif extension in ['.xlsx', '.xls']:
                df = pd.read_excel(ruta, dtype=str)
            else:
                # Intentar leer como CSV
                df = pd.read_csv(ruta, dtype=str)
            
            # Buscar columna DNI
            columna_dni = None
            for col in df.columns:
                if col.upper() in ['DNI', 'DOCUMENTO', 'NUMERO', 'NÚMERO', 'ID']:
                    columna_dni = col
                    break
            
            if columna_dni:
                dnis = df[columna_dni].dropna().astype(str).str.strip().str.zfill(8).tolist()
            else:
                # Usar primera columna
                dnis = df.iloc[:, 0].dropna().astype(str).str.strip().str.zfill(8).tolist()
            
            # Filtrar DNIs válidos (8 dígitos)
            dnis = [d for d in dnis if d.isdigit() and len(d) == 8]
            
            self._log(f"✓ DNIs leídos: {len(dnis)}")
            return dnis
            
        except Exception as e:
            self._log(f"✗ Error leyendo archivo: {e}")
            return []
    
    def _guardar_resultados(self, resultados: List[RegistroProfesional], suffix: str = ""):
        """Guarda los resultados en Excel, CSV y TXT"""
        if not resultados:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"resultados_sunedu{suffix}_{timestamp}"
        
        # Convertir a DataFrame
        datos = [asdict(r) for r in resultados]
        df = pd.DataFrame(datos)
        
        try:
            # Guardar Excel
            excel_path = self.dirs["output"] / f"{base_name}.xlsx"
            df.to_excel(excel_path, index=False, engine='openpyxl')
            self._log(f"💾 Excel guardado: {excel_path}")
        except Exception as e:
            self._log(f"⚠ Error guardando Excel: {e}")
        
        try:
            # Guardar CSV
            csv_path = self.dirs["output"] / f"{base_name}.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            self._log(f"💾 CSV guardado: {csv_path}")
        except Exception as e:
            self._log(f"⚠ Error guardando CSV: {e}")
        
        try:
            # Guardar TXT legible
            txt_path = self.dirs["output"] / f"{base_name}.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("RESULTADOS CONSULTA SUNEDU\n")
                f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                
                for r in resultados:
                    f.write(f"DNI: {r.dni}\n")
                    f.write(f"Nombres: {r.nombres}\n")
                    f.write(f"Grado/Título: {r.grado_o_titulo}\n")
                    f.write(f"Institución: {r.institucion}\n")
                    f.write(f"Fecha Diploma: {r.fecha_diploma}\n")
                    f.write(f"Fecha Matrícula: {r.fecha_matricula}\n")
                    f.write(f"Fecha Egreso: {r.fecha_egreso}\n")
                    f.write(f"Estado: {r.estado}\n")
                    f.write(f"Observaciones: {r.observaciones}\n")
                    f.write("-" * 80 + "\n")
            
            self._log(f"💾 TXT guardado: {txt_path}")
        except Exception as e:
            self._log(f"⚠ Error guardando TXT: {e}")
    
    def _mostrar_estadisticas(self):
        """Muestra resumen de estadísticas"""
        if not self.resultados:
            return
        
        total = len(self.resultados)
        encontrados = sum(1 for r in self.resultados if r.estado == "ENCONTRADO")
        no_encontrados = sum(1 for r in self.resultados if r.estado == "NO ENCONTRADO")
        errores = sum(1 for r in self.resultados if r.estado == "ERROR")
        pendientes = sum(1 for r in self.resultados if r.estado == "PENDIENTE")
        
        self._log("\n" + "=" * 60)
        self._log("📊 ESTADÍSTICAS FINALES")
        self._log("=" * 60)
        self._log(f"Total procesados:    {total}")
        self._log(f"✓ Encontrados:       {encontrados} ({encontrados/total*100:.1f}%)")
        self._log(f"✗ No encontrados:    {no_encontrados} ({no_encontrados/total*100:.1f}%)")
        self._log(f"⚠ Errores:           {errores} ({errores/total*100:.1f}%)")
        self._log(f"⏳ Pendientes:        {pendientes} ({pendientes/total*100:.1f}%)")
        self._log("=" * 60)


def main():
    """Función principal"""
    # Banner
    print("=" * 70)
    print("  ███████╗██╗   ██╗███╗   ██╗███████╗██████╗ ██╗   ██╗")
    print("  ██╔════╝██║   ██║████╗  ██║██╔════╝██╔══██╗██║   ██║")
    print("  ███████╗██║   ██║██╔██╗ ██║█████╗  ██║  ██║██║   ██║")
    print("  ╚════██║██║   ██║██║╚██╗██║██╔══╝  ██║  ██║██║   ██║")
    print("  ███████║╚██████╔╝██║ ╚████║███████╗██████╔╝╚██████╔╝")
    print("  ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚═════╝  ╚═════╝ ")
    print("                                                      ")
    print("     B O T   D E   C O N S U L T A   S U N E D U      ")
    print("=" * 70)
    print()
    
    # Verificar argumentos
    if len(sys.argv) < 2:
        print("Uso: python sunedu_bot.py <archivo_dnis.csv>")
        print("\nEjemplos:")
        print("  python sunedu_bot.py dnis.csv")
        print("  python sunedu_bot.py data/mis_dnis.xlsx")
        sys.exit(1)
    
    archivo_dnis = sys.argv[1]
    
    # Crear instancia del bot
    bot = SuneduBot()
    
    # Procesar lista de DNIs
    resultados = bot.procesar_lista_dnis(archivo_dnis)
    
    print("\n✓ Proceso completado")
    print(f"  Resultados guardados en: output/")
    print(f"  Screenshots guardados en: screenshots/")
    print(f"  Logs guardados en: logs/")


if __name__ == "__main__":
    main()

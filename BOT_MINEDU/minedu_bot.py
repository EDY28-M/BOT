#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MINEDU BOT - Consulta de títulos institutos tecnológicos/pedagógicos
Con resolución de captcha usando ddddocr
"""
import sys, time, random, logging, base64
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional

try:
    from botasaurus.browser import browser, Driver
except ImportError:
    print("[!] pip install botasaurus")
    sys.exit(1)

import pandas as pd
import ddddocr

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger("MINEDU")

@dataclass
class ResultadoMinedu:
    dni: str
    nombre_completo: str = ""
    titulo: str = ""
    institucion: str = ""
    fecha_expedicion: str = ""
    estado: str = "PENDIENTE"


class MineduBot:
    URL = "https://titulosinstitutos.minedu.gob.pe/"

    def __init__(self):
        self.output_dir = Path("resultados_minedu")
        self.output_dir.mkdir(exist_ok=True)
        self.resultados: List[ResultadoMinedu] = []
        self.ocr = ddddocr.DdddOcr(show_ad=False)

    def resolver_captcha(self, driver: Driver) -> str:
        """Resuelve el captcha usando ddddocr"""
        try:
            b64 = driver.run_js("""
                var img = document.querySelector('#imgCaptcha');
                return img ? img.src : null;
            """)
            if not b64 or "base64," not in b64:
                return ""
            b64 = b64.split("base64,")[1]
            img_bytes = base64.b64decode(b64)
            res = self.ocr.classification(img_bytes)
            log.info(f"[CAPTCHA] OCR: {res}")
            return res
        except Exception as e:
            log.error(f"[CAPTCHA] Error: {e}")
            return ""

    def consultar(self, driver: Driver, dni: str) -> Optional[ResultadoMinedu]:
        """Consulta un DNI en Minedu"""
        log.info(f"[MINEDU] {dni}")
        
        need_reload = True  # Controlar cuándo recargar la página
        
        for intento in range(1, 9):  # 8 intentos máximo
            try:
                log.info(f"[{intento}/8] Intento para DNI {dni}")
                
                # Recargar página si es necesario (primer intento o si refresh falló)
                if need_reload:
                    driver.get(self.URL)
                    time.sleep(2)
                    need_reload = False
                
                # Siempre ingresar DNI (puede haberse perdido al recargar)
                driver.run_js(f"""
                    var dniField = document.querySelector('#DOCU_NUM');
                    if (dniField) {{
                        dniField.value = '{dni}';
                        dniField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        dniField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                """)
                log.info(f"✓ DNI ingresado: {dni}")
                time.sleep(0.5)

                # Limpiar campo captcha antes de resolver
                driver.run_js("""
                    var cap = document.querySelector('#CaptchaCodeText');
                    if (cap) {
                        cap.removeAttribute('disabled');
                        cap.disabled = false;
                        cap.value = '';
                    }
                """)
                time.sleep(0.3)

                # Resolver captcha
                captcha_text = self.resolver_captcha(driver)
                if not captcha_text:
                    log.warning("[!] No se pudo resolver captcha, refrescando...")
                    if not self._refrescar_captcha(driver):
                        need_reload = True  # Si el refresh falla, recargar página
                    time.sleep(1)
                    continue

                time.sleep(0.5)

                # Ingresar captcha
                driver.run_js(f"""
                    var cap = document.querySelector('#CaptchaCodeText');
                    if (cap) {{
                        cap.removeAttribute('disabled');
                        cap.disabled = false;
                        cap.value = '{captcha_text}';
                        cap.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        cap.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        cap.dispatchEvent(new Event('keyup', {{ bubbles: true }}));
                    }}
                """)
                
                time.sleep(0.5)

                # Habilitar y hacer click en el botón de buscar
                clicked = driver.run_js("""
                    var btn = document.querySelector('#btnConsultar');
                    if (btn) {
                        btn.removeAttribute('disabled');
                        btn.disabled = false;
                        btn.classList.remove('inactivo');
                        btn.click();
                        return true;
                    }
                    return false;
                """)
                
                if not clicked:
                    log.warning("[!] No se pudo hacer click en buscar, recargando...")
                    need_reload = True
                    continue
                    
                time.sleep(3)

                # Detectar error de captcha
                error_info = self._detectar_error_captcha(driver)
                
                if error_info['hay_error']:
                    log.warning(f"[!] Captcha incorrecto detectado")
                    log.warning(f"    {error_info['mensaje'][:60]}")
                    
                    # Esperar a que el toast se muestre completamente
                    time.sleep(1)
                    
                    # Refrescar captcha y verificar que la imagen cambió
                    log.info("[↻] Refrescando captcha...")
                    if not self._refrescar_captcha(driver):
                        log.warning("[!] Refresh falló, recargando página completa...")
                        need_reload = True
                    time.sleep(1)
                    continue

                # Esperar resultado
                log.info("[...] Esperando resultados...")
                for _ in range(5):
                    resultado_html = driver.run_js("""
                        var div = document.querySelector('#divResultado');
                        return div ? div.innerHTML : '';
                    """)
                    if resultado_html and len(resultado_html) > 50:
                        log.info("✓ Resultados encontrados")
                        break
                    time.sleep(1)

                # Extraer datos
                if resultado_html:
                    datos = self._extraer_datos(driver, dni)
                    if datos:
                        log.info(f"✓ {datos.estado}: {datos.nombre_completo}")
                        return datos
                    else:
                        log.warning("[!] Extracción falló")

            except Exception as e:
                log.error(f"[!] Error en intento {intento}: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(1)

        log.warning(f"[X] DNI {dni} - No se pudo consultar después de 8 intentos")
        return ResultadoMinedu(dni=dni, estado="NO ENCONTRADO")

    def _detectar_error_captcha(self, driver: Driver) -> dict:
        """Detecta si hay error de captcha usando el toast message"""
        return driver.run_js("""
            var result = {
                hay_error: false,
                mensaje: '',
                toast_visible: false,
                validacion: ''
            };
            
            // 1. Verificar toast-message (el error que aparece y desaparece)
            var toast = document.querySelector('.toast-message');
            if (toast && toast.offsetParent !== null) {
                result.hay_error = true;
                result.toast_visible = true;
                result.mensaje = toast.innerText.trim();
                return result;
            }
            
            // 2. Verificar toast-container (aunque esté oculto)
            var toastContainer = document.querySelector('#toast-container');
            if (toastContainer) {
                var toastMsg = toastContainer.querySelector('.toast-message');
                if (toastMsg) {
                    var txt = toastMsg.innerText.trim();
                    if (txt) {
                        result.hay_error = true;
                        result.mensaje = txt;
                    }
                }
            }
            
            // 3. Verificar span de validación del campo
            var validation = document.querySelector('span[data-valmsg-for="CaptchaCodeText"]');
            if (validation && validation.innerText) {
                result.hay_error = true;
                result.validacion = validation.innerText.trim();
            }
            
            // 4. Verificar alerts
            var alerts = document.querySelectorAll('.alert-danger, .alert-warning');
            for (var i = 0; i < alerts.length; i++) {
                var txt = alerts[i].innerText.toLowerCase();
                if (txt.includes('captcha') || txt.includes('código') || txt.includes('verificación')) {
                    result.hay_error = true;
                    if (!result.mensaje) result.mensaje = alerts[i].innerText.trim();
                }
            }
            
            return result;
        """)
    
    def _refrescar_captcha(self, driver: Driver) -> bool:
        """Refresca el captcha haciendo click en el botón y verifica que la imagen cambie"""
        try:
            # 1. Guardar imagen ACTUAL antes de refrescar
            old_src = driver.run_js("""
                var img = document.querySelector('#imgCaptcha');
                return img ? img.src : null;
            """)
            
            # 2. Limpiar toasts/modales que puedan bloquear el click
            driver.run_js("""
                var toast = document.querySelector('#toast-container');
                if (toast) toast.remove();
                var swal = document.querySelector('.swal2-close');
                if (swal) swal.click();
            """)
            time.sleep(0.3)
            
            # 3. Refrescar con JS directo (MouseEvent dispatch)
            driver.run_js("""
                var btn = document.querySelector('#CapImageRefresh');
                if (btn) {
                    var evt = new MouseEvent('click', {bubbles: true, cancelable: true, view: window});
                    btn.dispatchEvent(evt);
                }
            """)
            
            # 4. Esperar a que la imagen REALMENTE cambie (máx 5 segundos)
            for wait in range(10):
                time.sleep(0.5)
                new_src = driver.run_js("""
                    var img = document.querySelector('#imgCaptcha');
                    return img ? img.src : null;
                """)
                if new_src and new_src != old_src:
                    log.info("✓ Captcha refrescado")
                    return True
            
            # 5. Último recurso: recargar la página completa
            log.warning("[!] Refresh no funcionó, recargando página...")
            return False
            
        except Exception as e:
            log.error(f"❌ Error al refrescar: {e}")
            return False

    def _extraer_datos(self, driver: Driver, dni: str) -> Optional[ResultadoMinedu]:
        """Extrae datos del resultado"""
        try:
            data = driver.run_js("""
                var result = {nombres: '', titulo: '', institucion: '', fecha: '', nivel: '', codigo: ''};
                var div = document.querySelector('#divResultado');
                if (!div) return null;
                
                // Buscar en las tablas de resultados
                var tables = div.querySelectorAll('table.gobpe-res-tabla-cuerpo');
                for (var t = 0; t < tables.length; t++) {
                    var rows = tables[t].querySelectorAll('tbody tr');
                    for (var i = 0; i < rows.length; i++) {
                        var cells = rows[i].querySelectorAll('td');
                        // Si solo hay 1 celda con colspan, es "no se encontraron"
                        if (cells.length === 1) continue;
                        
                        if (cells.length >= 3) {
                            // Columna 1: Nombres y DNI
                            var cell1 = cells[0].innerText.trim();
                            var lines1 = cell1.split('\\n');
                            if (lines1.length > 0) result.nombres = lines1[0].trim();
                            
                            // Columna 2: Título/Grado
                            var cell2 = cells[1].innerText.trim();
                            var lines2 = cell2.split('\\n');
                            for (var j = 0; j < lines2.length; j++) {
                                var line = lines2[j].trim();
                                if (!line.includes(':') && line.length > 5 && !result.titulo) {
                                    result.titulo = line;
                                }
                                if (line.includes('Nivel:')) result.nivel = line.replace('Nivel:', '').trim();
                                if (line.includes('Fecha de emisión:') || line.includes('Fecha emisión:')) {
                                    result.fecha = line.split(':')[1].trim();
                                }
                                if (line.includes('Código DRE:')) result.codigo = line.split(':')[1].trim();
                            }
                            
                            // Columna 3: Institución
                            var cell3 = cells[2].innerText.trim();
                            var lines3 = cell3.split('\\n');
                            if (lines3.length > 0) result.institucion = lines3[0].trim();
                            
                            // Si encontramos datos, salir
                            if (result.titulo) break;
                        }
                    }
                    if (result.titulo) break;
                }
                
                return result;
            """)
            
            if data and data.get('titulo'):
                info_extra = f"{data.get('nivel', '')} | {data.get('fecha', '')} | {data.get('codigo', '')}".strip(' |')
                return ResultadoMinedu(
                    dni=dni,
                    nombre_completo=data.get('nombres', ''),
                    titulo=data.get('titulo', ''),
                    institucion=data.get('institucion', ''),
                    fecha_expedicion=info_extra,
                    estado="ENCONTRADO"
                )
            else:
                return ResultadoMinedu(dni=dni, estado="NO ENCONTRADO")
        except Exception as e:
            log.error(f"[EXTRACT] Error: {e}")
            return ResultadoMinedu(dni=dni, estado="ERROR")

    def procesar_lista(self, archivo: str):
        """Procesa lista de DNIs"""
        dnis = self._leer_datos(archivo)
        if not dnis:
            log.error("No hay datos para procesar")
            return
        log.info(f"Total: {len(dnis)} registros")

        @browser(headless=False, block_images=False, window_size=(1200, 800))
        def ejecutar(driver: Driver, data):
            for i, dni in enumerate(data["dnis"], 1):
                log.info(f"[{i}/{len(data['dnis'])}]")
                r = self.consultar(driver, dni)
                if r:
                    self.resultados.append(r)
                if i % 5 == 0:
                    self._guardar("_prog")
                time.sleep(random.uniform(1, 2))
            return len(self.resultados)

        ejecutar({"dnis": dnis})
        self._guardar("_final")

    def _leer_datos(self, archivo: str) -> List[str]:
        """Lee DNIs del archivo"""
        try:
            df = pd.read_excel(archivo, dtype=str)
            # Filter only OK status if available
            if 'estado' in df.columns:
                df = df[df['estado'] == 'OK']
            
            # Get DNI column
            if 'dni' in df.columns:
                dnis = df['dni'].dropna().astype(str).str.strip().tolist()
                return [d for d in dnis if d and d != 'nan']
            return []
        except Exception as e:
            log.error(f"Error: {e}")
            return []

    def _guardar(self, sufijo=""):
        if not self.resultados: return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        df = pd.DataFrame([asdict(r) for r in self.resultados])
        path = self.output_dir / f"MINEDU{sufijo}_{ts}.xlsx"
        df.to_excel(path, index=False)
        log.info(f"Guardado: {path.name}")


if __name__ == "__main__":
    print("="*50)
    print("  MINEDU BOT - Títulos Institutos")
    print("="*50)
    archivo = sys.argv[1] if len(sys.argv) > 1 else "resultados/NOMBRES_final_20260209_090531.xlsx"
    MineduBot().procesar_lista(archivo)
    print("[OK] FIN")

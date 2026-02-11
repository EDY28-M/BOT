
import time
import re
import logging
from datetime import datetime
from typing import Dict, Any, List

from botasaurus.browser import Driver
from app.core.config import SUNEDU_URL, SUNEDU_SLEEP_NOT_FOUND, SUNEDU_MAX_RETRIES

log = logging.getLogger("SUNEDU")

class Motivo:
    NO_ENCONTRADO = "No se encontró en SUNEDU - derivado a MINEDU"
    CAPTCHA_FALLO = "Falló la verificación de seguridad/captcha en SUNEDU"
    VERIFICACION_NO_SUPERADA = "No se pasó la verificación de seguridad en SUNEDU"
    BOTON_NO_ENCONTRADO = "No se encontró el botón de búsqueda en SUNEDU"
    PAGINA_NO_CARGO = "La página de SUNEDU no cargó correctamente"
    ERROR_EXTRACCION = "Error al extraer datos de la tabla SUNEDU"
    TIMEOUT = "Tiempo de espera agotado"
    MAX_REINTENTOS = "Se agotaron todos los reintentos en SUNEDU"

class SuneduScraper:
    def __init__(self):
        self.url = SUNEDU_URL
        self._primera_carga = True

    def _detectar_estado(self, driver: Driver) -> str:
        try:
            return driver.run_js("""
                var tabla = document.querySelector('table.custom-table');
                if (tabla && tabla.querySelectorAll('tbody tr.ng-star-inserted').length > 0)
                    return 'tabla';
                var swal = document.querySelector('.swal2-html-container');
                if (swal) {
                    var txt = (swal.innerText || '').toLowerCase();
                    if (txt.includes('no se encontraron')) return 'no_encontrado';
                    if (txt.includes('verificaci') && txt.includes('fallid')) return 'verificacion_fallida';
                    if (txt.includes('verificaci') || txt.includes('seguridad')) return 'verificacion';
                }
                var cbs = document.querySelectorAll('input[type="checkbox"]');
                for (var i = 0; i < cbs.length; i++) {
                    if (!cbs[i].checked) return 'verificacion';
                }
                // Check iframes for Turnstile
                var iframes = document.querySelectorAll('iframe');
                for (var i = 0; i < iframes.length; i++) {
                    var src = iframes[i].src || '';
                    if (src.includes('turnstile') || src.includes('challenges')) {
                        var r = iframes[i].getBoundingClientRect();
                        if (r.width > 0 && r.height > 0) return 'verificacion';
                    }
                }
                return 'cargando';
            """)
        except Exception:
            return "cargando"

    def _cerrar_swal(self, driver: Driver):
        try:
            driver.run_js("""
                var btn = document.querySelector('button.swal2-close') ||
                          document.querySelector('button[aria-label="Close this dialog"]');
                if (btn) btn.click();
            """)
        except Exception:
            pass

    def _click_checkbox(self, driver: Driver) -> bool:
        try:
            # Try JS click first
            clicked = driver.run_js("""
                var cbs = document.querySelectorAll('input[type="checkbox"]');
                for (var i = 0; i < cbs.length; i++) {
                    if (!cbs[i].checked) {
                        cbs[i].click();
                        return true;
                    }
                }
                return false;
            """)
            if clicked: return True
            
            # Try Botasaurus method
            cb = driver.select('input[type="checkbox"]', wait=2)
            if cb:
                cb.click()
                return True
        except Exception:
            pass
        return False

    def _buscar_dni(self, driver: Driver, dni: str) -> bool:
        # Usar JS para llenar input (más rápido y confiable en Angular)
        dni_ok = driver.run_js(f"""
            var input = document.querySelector('input[formcontrolname="dni"]') ||
                        document.querySelector('input[type="text"]');
            if (!input) return false;
            
            // Angular reactive forms update
            var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(input, '{dni}');
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return true;
        """)
        if not dni_ok: return False

        time.sleep(0.5)

        # Click buscar
        btn_ok = driver.run_js("""
            var spans = document.querySelectorAll('span.p-button-label');
            for (var i = 0; i < spans.length; i++) {
                if (spans[i].textContent.trim() === 'Buscar') {
                    var btn = spans[i].closest('button');
                    if (btn) { btn.click(); return true; }
                }
            }
            return false;
        """)
        return bool(btn_ok)

    def _esperar_resultado(self, driver: Driver, timeout: int = 15) -> str:
        inicio = time.time()
        while time.time() - inicio < timeout:
            estado = self._detectar_estado(driver)
            if estado not in ("cargando",):
                # 'nada' logic handled by detection
                return estado
            time.sleep(0.5)
        return "timeout"

    def _extraer_datos(self, driver: Driver, dni: str) -> List[Dict[str, Any]]:
        try:
            data = driver.run_js("""
                var res = [];
                var tabla = document.querySelector('table.custom-table');
                if (!tabla) return res;
                var filas = tabla.querySelectorAll('tbody tr.ng-star-inserted');
                filas.forEach(function(fila) {
                    var celdas = fila.querySelectorAll('td');
                    if (celdas.length < 3) return;
                    
                    var ps1 = celdas[0].querySelectorAll('p');
                    var nombre = '', dniT = '';
                    ps1.forEach(p => {
                        var t = p.innerText.trim();
                        if (t.includes('DNI')) dniT = t;
                        else if (t.length > 3 && t.includes(',')) nombre = t;
                    });
                    
                    var ps2 = celdas[1].querySelectorAll('p');
                    var grado = '', fDip = '';
                    ps2.forEach(p => {
                        var t = p.innerText.trim(), tl = t.toLowerCase();
                        if (tl.includes('fecha de diploma:')) fDip = t.split(':').slice(1).join(':').trim();
                        else if (t.length > 5 && !tl.startsWith('grado') && !tl.startsWith('fecha')) grado = t;
                    });
                    
                    var ps3 = celdas[2].querySelectorAll('p');
                    var inst = '';
                    ps3.forEach(p => {
                        var tu = p.innerText.trim().toUpperCase();
                        if (tu.includes('UNIVERSIDAD') || tu.includes('INSTITUTO')) inst = p.innerText.trim();
                    });
                    
                    res.push({n: nombre, d: dniT, g: grado, i: inst, fd: fDip});
                });
                return res;
            """)
            if not data: return []

            registros = []
            for f in data:
                m = re.search(r"(\d{7,8})", f.get("d", ""))
                registros.append({
                    "dni": m.group(1) if m else dni,
                    "nombres": f.get("n", "").strip(),
                    "grado_o_titulo": f.get("g", "").strip(),
                    "institucion": f.get("i", "").strip(),
                    "fecha_diploma": f.get("fd", ""),
                    "fecha_consulta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
            return registros
        except Exception as e:
            log.error(f"Error extraccion: {e}")
            return []

    def procesar_dni(self, driver: Driver, dni: str) -> Dict[str, Any]:
        """Procesa un DNI. Retorna dict con resultado."""
        ultimo_motivo = Motivo.MAX_REINTENTOS
        
        for intento in range(1, SUNEDU_MAX_RETRIES + 1):
            try:
                pagina_fresca = False
                if self._primera_carga:
                    # Usar google_get si hay cloudflare
                    # driver.google_get(self.url, bypass_cloudflare=True) 
                    # Pero Sunedu suele ser accesible directo
                    driver.get(self.url)
                    time.sleep(6)
                    self._primera_carga = False
                    pagina_fresca = True
                elif intento > 1:
                    driver.run_js("location.reload();")
                    time.sleep(4)
                    pagina_fresca = True
                else:
                    self._cerrar_swal(driver)
                    time.sleep(0.3)

                # Verificar estado
                estado = self._detectar_estado(driver)
                
                # Intentar pasar verificación
                if estado in ("verificacion", "verificacion_fallida"):
                    self._click_checkbox(driver)
                    time.sleep(3)
                    estado = self._detectar_estado(driver)
                    if estado == "verificacion_fallida":
                         ultimo_motivo = Motivo.CAPTCHA_FALLO
                         continue # Reintenta con reload

                if not self._buscar_dni(driver, dni):
                    ultimo_motivo = Motivo.BOTON_NO_ENCONTRADO
                    continue

                res = self._esperar_resultado(driver)
                
                if res == "tabla":
                    datos = self._extraer_datos(driver, dni)
                    if datos:
                         time.sleep(SUNEDU_SLEEP_NOT_FOUND)
                         return {"encontrado": True, "datos": datos, "motivo": "Encontrado"}
                
                elif res == "no_encontrado":
                    self._cerrar_swal(driver)
                    time.sleep(SUNEDU_SLEEP_NOT_FOUND)
                    return {"encontrado": False, "datos": None, "motivo": Motivo.NO_ENCONTRADO}

                ultimo_motivo = f"Resultado inesperado: {res}"

            except Exception as e:
                 ultimo_motivo = f"Excepcion: {str(e)[:100]}"
                 self._primera_carga = True # Forzar recarga completa
        
        raise RuntimeError(ultimo_motivo)

"""
Workers de scraping refactorizados.

Cada worker encapsula la lógica de scraping de un bot original
y expone un método `procesar_un_dni(driver, dni) -> dict | None`.

El driver de botasaurus se gestiona dentro de la función decorada
con @browser, que permanece viva durante todo el ciclo del worker.
"""
import sys
import time
import random
import re
import logging
import base64
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List

try:
    from botasaurus.browser import browser, Driver
    BOTASAURUS_OK = True
except ImportError:
    BOTASAURUS_OK = False

from config import (
    Estado, SUNEDU_URL, MINEDU_URL,
    SUNEDU_SLEEP_MIN, SUNEDU_SLEEP_MAX,
    MINEDU_SLEEP_MIN, MINEDU_SLEEP_MAX,
    SUNEDU_MAX_RETRIES, MINEDU_MAX_RETRIES,
    WORKER_POLL_INTERVAL,
    HEADLESS, BLOCK_IMAGES_SUNEDU, BLOCK_IMAGES_MINEDU,
)
from database import tomar_siguiente, actualizar_resultado

log = logging.getLogger("WORKERS")


# ═══════════════════════════════════════════════════════════════════════
#  SUNEDU WORKER  (adaptado de sunedu_botasaurus.py)
# ═══════════════════════════════════════════════════════════════════════

class SuneduLogic:
    """Lógica de scraping de SUNEDU, independiente del ciclo de vida del driver."""

    URL = SUNEDU_URL

    def __init__(self):
        self._primera_carga = True

    # ── Detectar estado de la página ──
    def detectar_estado(self, driver: Driver) -> str:
        try:
            return driver.run_js("""
                var tabla = document.querySelector('table.custom-table');
                if (tabla && tabla.querySelectorAll('tbody tr.ng-star-inserted').length > 0)
                    return 'tabla';
                var swal = document.querySelector('.swal2-html-container');
                if (swal) {
                    var txt = (swal.innerText || '').toLowerCase();
                    if (txt.includes('no se encontraron')) return 'no_encontrado';
                    if (txt.includes('verificaci') || txt.includes('seguridad')) return 'verificacion';
                }
                var cbs = document.querySelectorAll('input[type="checkbox"]');
                for (var i = 0; i < cbs.length; i++) {
                    if (!cbs[i].checked) {
                        var r = cbs[i].getBoundingClientRect();
                        var p = (cbs[i].closest('label') || cbs[i].parentElement);
                        var pr = p ? p.getBoundingClientRect() : r;
                        if (r.width > 0 || r.height > 0 || pr.width > 0 || pr.height > 0)
                            return 'verificacion';
                    }
                }
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

    def cerrar_swal(self, driver: Driver):
        try:
            driver.run_js("""
                var btn = document.querySelector('button.swal2-close') ||
                          document.querySelector('button[aria-label="Close this dialog"]');
                if (btn) btn.click();
            """)
        except Exception:
            pass

    def click_checkbox(self, driver: Driver) -> bool:
        try:
            clicked = driver.run_js("""
                var cbs = document.querySelectorAll('input[type="checkbox"]');
                for (var i = 0; i < cbs.length; i++) {
                    if (!cbs[i].checked) {
                        cbs[i].click();
                        if (cbs[i].checked) return 'directo';
                        var parent = cbs[i].closest('label') || cbs[i].parentElement;
                        if (parent) { parent.click(); return 'parent'; }
                    }
                }
                var w = document.querySelector('.cf-turnstile') || document.querySelector('[data-sitekey]');
                if (w) { w.click(); return 'widget'; }
                return false;
            """)
            if clicked:
                log.info(f"[SUNEDU][CHECK] Click: {clicked}")
                return True
        except Exception:
            pass
        try:
            cb = driver.select('input[type="checkbox"]', wait=2)
            if cb:
                cb.click()
                return True
        except Exception:
            pass
        return False

    def buscar_dni(self, driver: Driver, dni: str) -> bool:
        dni_ok = driver.run_js(f"""
            var input = document.querySelector('input[formcontrolname="dni"]') ||
                        document.querySelector('input[type="text"]');
            if (!input) return false;
            var setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value').set;
            setter.call(input, '{dni}');
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return true;
        """)
        if not dni_ok:
            return False

        time.sleep(0.5)

        btn_ok = driver.run_js("""
            var spans = document.querySelectorAll('span.p-button-label');
            for (var i = 0; i < spans.length; i++) {
                if (spans[i].textContent.trim() === 'Buscar') {
                    var btn = spans[i].closest('button');
                    if (btn) { btn.click(); return true; }
                }
            }
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                if (btns[i].textContent.trim().includes('Buscar')) {
                    btns[i].click(); return true;
                }
            }
            return false;
        """)
        return bool(btn_ok)

    def esperar_resultado(self, driver: Driver, timeout: int = 15) -> str:
        inicio = time.time()
        while time.time() - inicio < timeout:
            estado = self.detectar_estado(driver)
            if estado != "cargando":
                return estado
            time.sleep(0.5)
        return "timeout"

    def extraer_datos(self, driver: Driver, dni: str) -> List[Dict[str, Any]]:
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
                    for (var i = 0; i < ps1.length; i++) {
                        var t = ps1[i].textContent.trim();
                        if (t.includes('DNI')) dniT = t;
                        else if (t.length > 3 && t.includes(',')) nombre = t;
                    }
                    var ps2 = celdas[1].querySelectorAll('p');
                    var grado = '', fDip = '';
                    for (var i = 0; i < ps2.length; i++) {
                        var t = ps2[i].textContent.trim(), tl = t.toLowerCase();
                        if (tl.includes('fecha de diploma:')) fDip = t.split(':').slice(1).join(':').trim();
                        else if (t.length > 5 && !tl.startsWith('grado') && !tl.startsWith('fecha') && !grado) grado = t;
                    }
                    var ps3 = celdas[2].querySelectorAll('p');
                    var inst = '';
                    for (var i = 0; i < ps3.length; i++) {
                        var tu = ps3[i].textContent.trim().toUpperCase();
                        if (tu.includes('UNIVERSIDAD') || tu.includes('INSTITUTO') || tu.includes('ESCUELA'))
                            inst = ps3[i].textContent.trim();
                    }
                    res.push({n: nombre, d: dniT, g: grado, i: inst, fd: fDip});
                });
                return res;
            """)
            if not data:
                return []

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
            log.error(f"[SUNEDU][EXTRACT] Error: {e}")
            return []

    # ── MÉTODO PRINCIPAL: procesar un solo DNI ──
    def procesar_un_dni(self, driver: Driver, dni: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retorna lista de dicts con datos si encuentra, None si no encuentra.
        Lanza Exception si falla tras todos los reintentos.
        """
        for intento in range(1, SUNEDU_MAX_RETRIES + 1):
            log.info(f"[SUNEDU] DNI {dni} | Intento {intento}/{SUNEDU_MAX_RETRIES}")
            try:
                # Cargar página
                if self._primera_carga:
                    log.info("[SUNEDU] Primera carga...")
                    driver.get(self.URL)
                    time.sleep(6)
                    self._primera_carga = False
                elif intento > 1:
                    log.info("[SUNEDU] Refrescando página...")
                    driver.run_js("location.reload(true);")
                    time.sleep(6)

                # Verificación pre-búsqueda
                estado = self.detectar_estado(driver)
                if estado == "verificacion":
                    log.info("[SUNEDU] Verificación detectada...")
                    self.cerrar_swal(driver)
                    time.sleep(0.5)
                    self.click_checkbox(driver)
                    time.sleep(2)
                    estado = self.detectar_estado(driver)
                    if estado == "verificacion":
                        log.warning("[SUNEDU] Verificación no superada → reintentar")
                        continue
                    time.sleep(1)

                # Buscar DNI
                if not self.buscar_dni(driver, dni):
                    time.sleep(2)
                    continue

                time.sleep(1)

                # Esperar resultado
                resultado = self.esperar_resultado(driver, timeout=15)

                if resultado == "tabla":
                    datos = self.extraer_datos(driver, dni)
                    if datos:
                        time.sleep(4)
                        return datos
                    return None

                elif resultado == "no_encontrado":
                    self.cerrar_swal(driver)
                    time.sleep(4)
                    return None  # No encontrado → pasar a Minedu

                elif resultado == "verificacion":
                    log.warning("[SUNEDU] Verificación post-búsqueda")
                    self.cerrar_swal(driver)
                    time.sleep(0.5)
                    self.click_checkbox(driver)
                    time.sleep(2)
                    post = self.detectar_estado(driver)
                    if post == "tabla":
                        datos = self.extraer_datos(driver, dni)
                        if datos:
                            return datos
                        return None
                    elif post == "no_encontrado":
                        self.cerrar_swal(driver)
                        time.sleep(4)
                        return None
                    else:
                        continue

                elif resultado == "timeout":
                    log.warning("[SUNEDU] Timeout → reintentar")
                    continue

            except Exception as e:
                log.error(f"[SUNEDU] Error intento {intento}: {e}")
                time.sleep(2)

        raise RuntimeError(f"SUNEDU: Sin resultado tras {SUNEDU_MAX_RETRIES} intentos para DNI {dni}")


# ═══════════════════════════════════════════════════════════════════════
#  MINEDU WORKER  (adaptado de minedu_bot.py)
# ═══════════════════════════════════════════════════════════════════════

class MineduLogic:
    """Lógica de scraping de MINEDU con resolución de captcha OCR."""

    URL = MINEDU_URL

    def __init__(self):
        try:
            import ddddocr
            self.ocr = ddddocr.DdddOcr(show_ad=False)
        except ImportError:
            log.error("[MINEDU] ddddocr no instalado. pip install ddddocr")
            self.ocr = None

    def resolver_captcha(self, driver: Driver) -> str:
        if not self.ocr:
            return ""
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
            log.info(f"[MINEDU][CAPTCHA] OCR: {res}")
            return res
        except Exception as e:
            log.error(f"[MINEDU][CAPTCHA] Error: {e}")
            return ""

    def _detectar_error_captcha(self, driver: Driver) -> dict:
        return driver.run_js("""
            var result = { hay_error: false, mensaje: '' };
            var toast = document.querySelector('.toast-message');
            if (toast && toast.offsetParent !== null) {
                result.hay_error = true;
                result.mensaje = toast.innerText.trim();
                return result;
            }
            var tc = document.querySelector('#toast-container');
            if (tc) {
                var tm = tc.querySelector('.toast-message');
                if (tm) {
                    var txt = tm.innerText.trim();
                    if (txt) { result.hay_error = true; result.mensaje = txt; }
                }
            }
            var val = document.querySelector('span[data-valmsg-for="CaptchaCodeText"]');
            if (val && val.innerText) { result.hay_error = true; if (!result.mensaje) result.mensaje = val.innerText.trim(); }
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
        try:
            old_src = driver.run_js("""
                var img = document.querySelector('#imgCaptcha');
                return img ? img.src : null;
            """)
            driver.run_js("""
                var toast = document.querySelector('#toast-container');
                if (toast) toast.remove();
                var swal = document.querySelector('.swal2-close');
                if (swal) swal.click();
            """)
            time.sleep(0.3)
            driver.run_js("""
                var btn = document.querySelector('#CapImageRefresh');
                if (btn) {
                    var evt = new MouseEvent('click', {bubbles: true, cancelable: true, view: window});
                    btn.dispatchEvent(evt);
                }
            """)
            for _ in range(10):
                time.sleep(0.5)
                new_src = driver.run_js("""
                    var img = document.querySelector('#imgCaptcha');
                    return img ? img.src : null;
                """)
                if new_src and new_src != old_src:
                    return True
            return False
        except Exception:
            return False

    def _extraer_datos(self, driver: Driver, dni: str) -> Optional[Dict[str, Any]]:
        try:
            data = driver.run_js("""
                var result = {nombres: '', titulo: '', institucion: '', fecha: '', nivel: '', codigo: ''};
                var div = document.querySelector('#divResultado');
                if (!div) return null;
                var tables = div.querySelectorAll('table.gobpe-res-tabla-cuerpo');
                for (var t = 0; t < tables.length; t++) {
                    var rows = tables[t].querySelectorAll('tbody tr');
                    for (var i = 0; i < rows.length; i++) {
                        var cells = rows[i].querySelectorAll('td');
                        if (cells.length === 1) continue;
                        if (cells.length >= 3) {
                            var cell1 = cells[0].innerText.trim();
                            var lines1 = cell1.split('\\n');
                            if (lines1.length > 0) result.nombres = lines1[0].trim();

                            var cell2 = cells[1].innerText.trim();
                            var lines2 = cell2.split('\\n');
                            for (var j = 0; j < lines2.length; j++) {
                                var line = lines2[j].trim();
                                if (!line.includes(':') && line.length > 5 && !result.titulo) result.titulo = line;
                                if (line.includes('Nivel:')) result.nivel = line.replace('Nivel:', '').trim();
                                if (line.includes('Fecha de emisión:') || line.includes('Fecha emisión:'))
                                    result.fecha = line.split(':')[1].trim();
                                if (line.includes('Código DRE:')) result.codigo = line.split(':')[1].trim();
                            }

                            var cell3 = cells[2].innerText.trim();
                            var lines3 = cell3.split('\\n');
                            if (lines3.length > 0) result.institucion = lines3[0].trim();

                            if (result.titulo) break;
                        }
                    }
                    if (result.titulo) break;
                }
                return result;
            """)
            if data and data.get("titulo"):
                return {
                    "nombre_completo": data.get("nombres", ""),
                    "titulo": data.get("titulo", ""),
                    "institucion": data.get("institucion", ""),
                    "nivel": data.get("nivel", ""),
                    "fecha_expedicion": data.get("fecha", ""),
                    "codigo_dre": data.get("codigo", ""),
                    "fecha_consulta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            return None
        except Exception as e:
            log.error(f"[MINEDU][EXTRACT] Error: {e}")
            return None

    # ── MÉTODO PRINCIPAL: procesar un solo DNI ──
    def procesar_un_dni(self, driver: Driver, dni: str) -> Optional[Dict[str, Any]]:
        """
        Retorna dict con datos si encuentra, None si no encuentra.
        Lanza Exception si falla tras todos los reintentos.
        """
        need_reload = True

        for intento in range(1, MINEDU_MAX_RETRIES + 1):
            log.info(f"[MINEDU] DNI {dni} | Intento {intento}/{MINEDU_MAX_RETRIES}")
            try:
                if need_reload:
                    driver.get(self.URL)
                    time.sleep(2)
                    need_reload = False

                # Ingresar DNI
                driver.run_js(f"""
                    var dniField = document.querySelector('#DOCU_NUM');
                    if (dniField) {{
                        dniField.value = '{dni}';
                        dniField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        dniField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                """)
                time.sleep(0.5)

                # Limpiar campo captcha
                driver.run_js("""
                    var cap = document.querySelector('#CaptchaCodeText');
                    if (cap) { cap.removeAttribute('disabled'); cap.disabled = false; cap.value = ''; }
                """)
                time.sleep(0.3)

                # Resolver captcha
                captcha_text = self.resolver_captcha(driver)
                if not captcha_text:
                    if not self._refrescar_captcha(driver):
                        need_reload = True
                    time.sleep(1)
                    continue

                time.sleep(0.5)

                # Ingresar captcha
                driver.run_js(f"""
                    var cap = document.querySelector('#CaptchaCodeText');
                    if (cap) {{
                        cap.removeAttribute('disabled'); cap.disabled = false;
                        cap.value = '{captcha_text}';
                        cap.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        cap.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        cap.dispatchEvent(new Event('keyup', {{ bubbles: true }}));
                    }}
                """)
                time.sleep(0.5)

                # Click buscar
                clicked = driver.run_js("""
                    var btn = document.querySelector('#btnConsultar');
                    if (btn) {
                        btn.removeAttribute('disabled'); btn.disabled = false;
                        btn.classList.remove('inactivo'); btn.click(); return true;
                    }
                    return false;
                """)
                if not clicked:
                    need_reload = True
                    continue

                time.sleep(3)

                # Error de captcha?
                error_info = self._detectar_error_captcha(driver)
                if error_info["hay_error"]:
                    log.warning(f"[MINEDU] Captcha incorrecto: {error_info['mensaje'][:60]}")
                    time.sleep(1)
                    if not self._refrescar_captcha(driver):
                        need_reload = True
                    time.sleep(1)
                    continue

                # Esperar resultado
                resultado_html = ""
                for _ in range(5):
                    resultado_html = driver.run_js("""
                        var div = document.querySelector('#divResultado');
                        return div ? div.innerHTML : '';
                    """)
                    if resultado_html and len(resultado_html) > 50:
                        break
                    time.sleep(1)

                if resultado_html:
                    datos = self._extraer_datos(driver, dni)
                    if datos:
                        return datos
                    return None  # No encontrado

            except Exception as e:
                log.error(f"[MINEDU] Error intento {intento}: {e}")
                need_reload = True
                time.sleep(1)

        raise RuntimeError(f"MINEDU: Sin resultado tras {MINEDU_MAX_RETRIES} intentos para DNI {dni}")


# ═══════════════════════════════════════════════════════════════════════
#  FUNCIONES DE LOOP PARA LOS WORKERS (ejecutados dentro de @browser)
# ═══════════════════════════════════════════════════════════════════════

def sunedu_worker_loop(stop_event: threading.Event):
    """
    Función que ejecuta el worker de Sunedu dentro de un hilo.
    Gestiona el ciclo de vida del driver con @browser.
    """
    log.info("[SUNEDU WORKER] Iniciando...")

    @browser(headless=HEADLESS, block_images=BLOCK_IMAGES_SUNEDU, window_size=(1366, 768))
    def _loop(driver: Driver, data):
        evt: threading.Event = data["stop_event"]
        logic = SuneduLogic()
        procesados = 0

        while not evt.is_set():
            # Tomar siguiente DNI en estado PENDIENTE
            reg = tomar_siguiente(Estado.PENDIENTE, Estado.PROCESANDO_SUNEDU)
            if reg is None:
                # No hay trabajo → esperar
                evt.wait(timeout=WORKER_POLL_INTERVAL)
                continue

            log.info(f"[SUNEDU WORKER] Procesando DNI {reg.dni} (id={reg.id})")
            try:
                resultado = logic.procesar_un_dni(driver, reg.dni)
                if resultado:
                    # Encontrado en SUNEDU → guardar payload
                    # resultado es una lista de dicts (puede haber múltiples grados)
                    payload = resultado if isinstance(resultado, list) else [resultado]
                    actualizar_resultado(
                        reg.id,
                        Estado.FOUND_SUNEDU,
                        payload_sunedu={
                            "registros": payload,
                            "total": len(payload),
                            "nombres": payload[0].get("nombres", ""),
                            "grado_o_titulo": payload[0].get("grado_o_titulo", ""),
                            "institucion": payload[0].get("institucion", ""),
                            "fecha_diploma": payload[0].get("fecha_diploma", ""),
                        },
                    )
                    log.info(f"[SUNEDU WORKER] DNI {reg.dni} → FOUND_SUNEDU ({len(payload)} registro(s))")
                else:
                    # No encontrado → pasar a Minedu
                    actualizar_resultado(reg.id, Estado.CHECK_MINEDU)
                    log.info(f"[SUNEDU WORKER] DNI {reg.dni} → CHECK_MINEDU")

            except Exception as e:
                log.error(f"[SUNEDU WORKER] Error DNI {reg.dni}: {e}")
                actualizar_resultado(
                    reg.id, Estado.ERROR_SUNEDU, error_msg=str(e)[:500]
                )

            procesados += 1
            # Sleep anti-ban
            time.sleep(random.uniform(SUNEDU_SLEEP_MIN, SUNEDU_SLEEP_MAX))

        log.info(f"[SUNEDU WORKER] Detenido. Procesados: {procesados}")
        return procesados

    try:
        result = _loop({"stop_event": stop_event})
        log.info(f"[SUNEDU WORKER] Finalizado con {result} procesados")
    except Exception as e:
        log.error(f"[SUNEDU WORKER] Crash fatal: {e}")


def minedu_worker_loop(stop_event: threading.Event):
    """
    Función que ejecuta el worker de Minedu dentro de un hilo.
    Gestiona el ciclo de vida del driver con @browser.
    """
    log.info("[MINEDU WORKER] Iniciando...")

    @browser(headless=HEADLESS, block_images=BLOCK_IMAGES_MINEDU, window_size=(1200, 800))
    def _loop(driver: Driver, data):
        evt: threading.Event = data["stop_event"]
        logic = MineduLogic()
        procesados = 0

        while not evt.is_set():
            # Tomar siguiente DNI en estado CHECK_MINEDU
            reg = tomar_siguiente(Estado.CHECK_MINEDU, Estado.PROCESANDO_MINEDU)
            if reg is None:
                evt.wait(timeout=WORKER_POLL_INTERVAL)
                continue

            log.info(f"[MINEDU WORKER] Procesando DNI {reg.dni} (id={reg.id})")
            try:
                resultado = logic.procesar_un_dni(driver, reg.dni)
                if resultado:
                    actualizar_resultado(
                        reg.id,
                        Estado.FOUND_MINEDU,
                        payload_minedu={
                            "nombre_completo": resultado.get("nombre_completo", ""),
                            "titulo": resultado.get("titulo", ""),
                            "institucion": resultado.get("institucion", ""),
                            "fecha_expedicion": resultado.get("fecha_expedicion", ""),
                            "nivel": resultado.get("nivel", ""),
                            "codigo_dre": resultado.get("codigo_dre", ""),
                        },
                    )
                    log.info(f"[MINEDU WORKER] DNI {reg.dni} → FOUND_MINEDU")
                else:
                    actualizar_resultado(reg.id, Estado.NOT_FOUND)
                    log.info(f"[MINEDU WORKER] DNI {reg.dni} → NOT_FOUND")

            except Exception as e:
                log.error(f"[MINEDU WORKER] Error DNI {reg.dni}: {e}")
                actualizar_resultado(
                    reg.id, Estado.ERROR_MINEDU, error_msg=str(e)[:500]
                )

            procesados += 1
            time.sleep(random.uniform(MINEDU_SLEEP_MIN, MINEDU_SLEEP_MAX))

        log.info(f"[MINEDU WORKER] Detenido. Procesados: {procesados}")
        return procesados

    try:
        result = _loop({"stop_event": stop_event})
        log.info(f"[MINEDU WORKER] Finalizado con {result} procesados")
    except Exception as e:
        log.error(f"[MINEDU WORKER] Crash fatal: {e}")

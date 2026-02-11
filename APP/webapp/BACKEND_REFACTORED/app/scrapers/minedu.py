
import time
import base64
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from botasaurus.browser import Driver
from app.core.config import MINEDU_URL, MINEDU_MAX_RETRIES

log = logging.getLogger("MINEDU")

# ═══ Monitoreo Profesional — Script espía inyectado via CDP ═══════════════
MONITOR_INIT_SCRIPT = """
(function() {
    if (window.__monitorActive) return;
    window.__monitorActive = true;
    window.__capturedEvents = [];
    function pushEvent(data) {
        if (window.__capturedEvents.length > 300) window.__capturedEvents.shift();
        data.ts = new Date().toISOString();
        window.__capturedEvents.push(data);
    }
    window.onerror = function(message, source, lineno, colno, error) {
        pushEvent({ type: 'JS_ERROR', message: String(message), source: String(source || ''), line: lineno, stack: error ? String(error.stack || '').substring(0, 300) : '' });
    };
    window.addEventListener('unhandledrejection', function(event) {
        pushEvent({ type: 'PROMISE_ERROR', message: event.reason ? String(event.reason.message || event.reason).substring(0, 300) : 'unknown' });
    });
    ['log', 'warn', 'error', 'info'].forEach(function(level) {
        var original = console[level];
        console[level] = function() {
            pushEvent({ type: 'CONSOLE', level: level, message: Array.from(arguments).map(function(a) { return String(a); }).join(' ').substring(0, 400) });
            original.apply(console, arguments);
        };
    });
    var originalFetch = window.fetch;
    window.fetch = function() {
        var url = arguments[0], opts = arguments[1] || {}, method = opts.method || 'GET';
        return originalFetch.apply(this, arguments).then(function(r) {
            if (!r.ok) pushEvent({ type: 'HTTP_ERROR', url: String(url).substring(0, 200), status: r.status, method: method });
            return r;
        }).catch(function(e) {
            pushEvent({ type: 'NETWORK_ERROR', url: String(url).substring(0, 200), method: method, message: String(e.message).substring(0, 200) });
            throw e;
        });
    };
    var origOpen = XMLHttpRequest.prototype.open, origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(m, u) { this.__monMethod = m; this.__monUrl = String(u).substring(0, 200); origOpen.apply(this, arguments); };
    XMLHttpRequest.prototype.send = function() {
        var self = this;
        this.addEventListener('error', function() { pushEvent({ type: 'NETWORK_ERROR', method: self.__monMethod, url: self.__monUrl, message: 'XHR failed' }); });
        this.addEventListener('load', function() { if (self.status >= 400) pushEvent({ type: 'HTTP_ERROR', method: self.__monMethod, url: self.__monUrl, status: self.status }); });
        origSend.apply(this, arguments);
    };
})();
"""

class Motivo:
    MINEDU_NO_ENCONTRADO = "No se encontró título en MINEDU"
    MINEDU_CAPTCHA_FALLO = "Falló la verificación del captcha en MINEDU"
    MINEDU_CAPTCHA_INCORRECTO = "Captcha incorrecto en MINEDU - reintentando"
    MINEDU_OCR_FALLO = "Falló el OCR del captcha en MINEDU"
    MINEDU_BOTON_NO_ENCONTRADO = "No se encontró el botón de consulta en MINEDU"
    MINEDU_PAGINA_NO_CARGO = "La página de MINEDU no cargó correctamente"
    MINEDU_TIMEOUT = "Tiempo de espera agotado en MINEDU"
    MINEDU_MAX_REINTENTOS = "Se agotaron todos los reintentos en MINEDU"
    MINEDU_REFRESCO_CAPTCHA_FALLO = "No se pudo refrescar el captcha en MINEDU"

# Alias for compatibility if needed
NO_ENCONTRADO = Motivo.MINEDU_NO_ENCONTRADO
CAPTCHA_INCORRECTO = Motivo.MINEDU_CAPTCHA_INCORRECTO
OCR_FALLO = Motivo.MINEDU_OCR_FALLO
BOTON_NO_ENCONTRADO = Motivo.MINEDU_BOTON_NO_ENCONTRADO
TIMEOUT = Motivo.MINEDU_TIMEOUT
MAX_REINTENTOS = Motivo.MINEDU_MAX_REINTENTOS
REFRESCO_CAPTCHA_FALLO = Motivo.MINEDU_REFRESCO_CAPTCHA_FALLO


class MineduScraper:
    """Lógica de scraping de MINEDU con resolución de captcha OCR."""

    URL = MINEDU_URL

    def __init__(self):
        self._cdp_configured = False
        try:
            import ddddocr
            self.ocr = ddddocr.DdddOcr(show_ad=False)
        except ImportError:
            log.error("[MINEDU] ddddocr no instalado. pip install ddddocr")
            self.ocr = None

    # ═══ Monitoreo Profesional — CDP Bridge ═══════════════════════════
    def _setup_cdp_monitoring(self, driver: Driver):
        if self._cdp_configured:
            return
        try:
            selenium_driver = getattr(driver, '_driver', None) or getattr(driver, 'driver', None)
            if selenium_driver and hasattr(selenium_driver, 'execute_cdp_cmd'):
                selenium_driver.execute_cdp_cmd(
                    'Page.addScriptToEvaluateOnNewDocument',
                    {'source': MONITOR_INIT_SCRIPT}
                )
                self._cdp_configured = True
                log.info("[MONITOR] ✅ CDP monitoring configurado para MINEDU")
                return
        except Exception as e:
            log.warning(f"[MONITOR] CDP no disponible: {e}")
        self._inject_monitor_fallback(driver)

    def _inject_monitor_fallback(self, driver: Driver):
        try:
            driver.run_js(MONITOR_INIT_SCRIPT)
        except Exception:
            pass

    def _collect_events(self, driver: Driver, context: str = ""):
        try:
            events = driver.run_js("var e = window.__capturedEvents || []; window.__capturedEvents = []; return e;")
            if not events: return
            for evt in events:
                tipo = evt.get('type', 'UNKNOWN')
                level = evt.get('level', '')
                if tipo == 'CONSOLE':
                    msg = f"[BROWSER][CONSOLE.{level.upper()}] {evt.get('message', '')}"
                elif tipo == 'JS_ERROR':
                    msg = f"[BROWSER][JS_ERROR] {evt.get('message', '')} @ {evt.get('source', '')}:{evt.get('line', '')}"
                elif tipo == 'HTTP_ERROR':
                    msg = f"[BROWSER][HTTP_{evt.get('status', '???')}] {evt.get('method', '')} {evt.get('url', '')}"
                elif tipo == 'NETWORK_ERROR':
                    msg = f"[BROWSER][NET_FAIL] {evt.get('method', '')} {evt.get('url', '')} — {evt.get('message', '')}"
                else:
                    msg = f"[BROWSER][{tipo}] {evt}"
                if context: msg = f"[{context}] {msg}"
                if tipo in ('JS_ERROR', 'NETWORK_ERROR', 'PROMISE_ERROR'):
                    log.error(msg)
                elif tipo == 'HTTP_ERROR':
                    log.warning(msg)
                else:
                    log.debug(msg)
        except Exception:
            pass

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
            time.sleep(0.5)
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

    # ── MÉTODO PRINCIPAL: procesar un solo DNI (Alias para compatibilidad) ──
    def procesar_dni(self, driver: Driver, dni: str) -> Dict[str, Any]:
        return self.procesar_un_dni(driver, dni)

    def procesar_un_dni(self, driver: Driver, dni: str) -> Dict[str, Any]:
        """
        Retorna dict con:
          - 'encontrado': bool
          - 'datos': dict si encontrado
          - 'motivo': str razón legible del resultado
        Lanza Exception si falla tras todos los reintentos.
        """
        need_reload = True
        ultimo_motivo = Motivo.MINEDU_MAX_REINTENTOS

        for intento in range(1, MINEDU_MAX_RETRIES + 1):
            log.info(f"[MINEDU] DNI {dni} | Intento {intento}/{MINEDU_MAX_RETRIES}")
            try:
                if need_reload:
                    driver.get(self.URL)
                    time.sleep(2)  # carga rápida (Bot: 2s)
                    need_reload = False
                    self._setup_cdp_monitoring(driver)
                    if not self._cdp_configured:
                        self._inject_monitor_fallback(driver)

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
                    ultimo_motivo = Motivo.MINEDU_OCR_FALLO
                    if not self._refrescar_captcha(driver):
                        need_reload = True
                        ultimo_motivo = Motivo.MINEDU_REFRESCO_CAPTCHA_FALLO
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

                # Click buscar (Logic from minedu_bot.py)
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
                    need_reload = True
                    ultimo_motivo = Motivo.MINEDU_BOTON_NO_ENCONTRADO
                    continue

                time.sleep(3)  # Espera post-click del Bot

                # Collect browser logs after search
                self._collect_events(driver, f"DNI={dni} POST_SEARCH")

                # Error de captcha?
                error_info = self._detectar_error_captcha(driver)
                if error_info["hay_error"]:
                    log.warning(f"[MINEDU] Captcha incorrecto: {error_info['mensaje'][:60]}")
                    ultimo_motivo = f"{Motivo.MINEDU_CAPTCHA_INCORRECTO}: {error_info['mensaje'][:100]}"
                    time.sleep(1)
                    if not self._refrescar_captcha(driver):
                        need_reload = True
                        ultimo_motivo = Motivo.MINEDU_REFRESCO_CAPTCHA_FALLO
                    time.sleep(1)
                    continue

                # Collect logs before checking results
                self._collect_events(driver, f"DNI={dni} PRE_RESULT")

                # Esperar resultado
                resultado_html = ""
                for _ in range(5): # Bot uses 5 check attempts
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
                        return {"encontrado": True, "datos": datos, "motivo": "Encontrado en MINEDU"}
                    return {"encontrado": False, "datos": None, "motivo": Motivo.MINEDU_NO_ENCONTRADO}
                else:
                    ultimo_motivo = Motivo.MINEDU_TIMEOUT

            except Exception as e:
                log.error(f"[MINEDU] Error intento {intento}: {e}")
                self._collect_events(driver, f"DNI={dni} EXCEPTION")
                need_reload = True
                ultimo_motivo = f"{Motivo.MINEDU_PAGINA_NO_CARGO}: {str(e)[:200]}"
                time.sleep(2)

        raise RuntimeError(f"{Motivo.MINEDU_MAX_REINTENTOS} ({MINEDU_MAX_RETRIES} intentos) | Último motivo: {ultimo_motivo}")

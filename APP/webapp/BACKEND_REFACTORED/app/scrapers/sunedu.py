
import time
import re
import logging
from datetime import datetime
from typing import Dict, Any, List

from botasaurus.browser import Driver
from app.core.config import SUNEDU_URL, SUNEDU_MAX_RETRIES

log = logging.getLogger("SUNEDU")

# ═══════════════════════════════════════════════════════════════════════
# MONITOREO PROFESIONAL — Script espía inyectado via CDP
# Equivalente a Playwright: page.addInitScript() + page.exposeFunction()
# Se ejecuta ANTES del JS de la web, intercepta TODO desde el inicio.
# ═══════════════════════════════════════════════════════════════════════
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

    // 1. JS Errors
    window.onerror = function(message, source, lineno, colno, error) {
        pushEvent({
            type: 'JS_ERROR',
            message: String(message),
            source: String(source || ''),
            line: lineno,
            column: colno,
            stack: error ? String(error.stack || '').substring(0, 300) : ''
        });
    };

    // 2. Unhandled Promise Rejections
    window.addEventListener('unhandledrejection', function(event) {
        pushEvent({
            type: 'PROMISE_ERROR',
            message: event.reason ? String(event.reason.message || event.reason).substring(0, 300) : 'unknown',
            stack: event.reason ? String(event.reason.stack || '').substring(0, 300) : ''
        });
    });

    // 3. Console Interception
    ['log', 'warn', 'error', 'info', 'debug'].forEach(function(level) {
        var original = console[level];
        console[level] = function() {
            pushEvent({
                type: 'CONSOLE',
                level: level,
                message: Array.from(arguments).map(function(a) { return String(a); }).join(' ').substring(0, 400)
            });
            original.apply(console, arguments);
        };
    });

    // 4. Fetch Interception
    var originalFetch = window.fetch;
    window.fetch = function() {
        var url = arguments[0];
        var opts = arguments[1] || {};
        var method = opts.method || 'GET';
        return originalFetch.apply(this, arguments).then(function(response) {
            if (!response.ok) {
                pushEvent({
                    type: 'HTTP_ERROR',
                    url: String(url).substring(0, 200),
                    status: response.status,
                    method: method
                });
            }
            return response;
        }).catch(function(err) {
            pushEvent({
                type: 'NETWORK_ERROR',
                url: String(url).substring(0, 200),
                method: method,
                message: String(err.message).substring(0, 200)
            });
            throw err;
        });
    };

    // 5. XHR Interception
    var origOpen = XMLHttpRequest.prototype.open;
    var origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(method, url) {
        this.__monMethod = method;
        this.__monUrl = String(url).substring(0, 200);
        origOpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function() {
        var self = this;
        this.addEventListener('error', function() {
            pushEvent({ type: 'NETWORK_ERROR', method: self.__monMethod, url: self.__monUrl, message: 'XHR failed' });
        });
        this.addEventListener('load', function() {
            if (self.status >= 400) {
                pushEvent({ type: 'HTTP_ERROR', method: self.__monMethod, url: self.__monUrl, status: self.status });
            }
        });
        origSend.apply(this, arguments);
    };
})();
"""


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
    """
    Scraper SUNEDU con Botasaurus.
    Lógica portada DIRECTAMENTE de sunedu_botasaurus.py + monitoreo profesional CDP.
    """

    URL = SUNEDU_URL

    def __init__(self):
        self._primera_carga = True
        self._cdp_configured = False

    # ═══════════════════════════════════════════════════════════════════
    # MONITOREO PROFESIONAL — CDP Bridge
    # ═══════════════════════════════════════════════════════════════════

    def _setup_cdp_monitoring(self, driver: Driver):
        """
        Configura monitoreo via CDP (Chrome DevTools Protocol).
        Equivalente a Playwright's page.addInitScript():
        - Se ejecuta ANTES del JS de la página
        - Intercepta console, errors, fetch, XHR desde el inicio
        """
        if self._cdp_configured:
            return

        try:
            # Acceder al driver Selenium subyacente para CDP
            selenium_driver = getattr(driver, '_driver', None) or getattr(driver, 'driver', None)
            if selenium_driver and hasattr(selenium_driver, 'execute_cdp_cmd'):
                selenium_driver.execute_cdp_cmd(
                    'Page.addScriptToEvaluateOnNewDocument',
                    {'source': MONITOR_INIT_SCRIPT}
                )
                self._cdp_configured = True
                log.info("[MONITOR] ✅ CDP monitoring configurado (pre-load injection)")
                return
        except Exception as e:
            log.warning(f"[MONITOR] CDP no disponible ({e}), usando post-load injection")

        # Fallback: inyectar después de cargar (menos ideal pero funcional)
        self._inject_monitor_fallback(driver)

    def _inject_monitor_fallback(self, driver: Driver):
        """Fallback: inyecta el monitor DESPUÉS de que la página carga."""
        try:
            driver.run_js(MONITOR_INIT_SCRIPT)
        except Exception:
            pass

    def _collect_events(self, driver: Driver, context: str = "") -> List[Dict]:
        """
        Recoge todos los eventos capturados del navegador y los loguea.
        Retorna la lista de eventos para análisis.
        """
        try:
            events = driver.run_js("""
                var evts = window.__capturedEvents || [];
                window.__capturedEvents = [];
                return evts;
            """)
            if not events:
                return []

            for evt in events:
                tipo = evt.get("type", "UNKNOWN")
                level = evt.get("level", "")

                # Construir mensaje legible
                if tipo == "CONSOLE":
                    msg = f"[BROWSER][CONSOLE.{level.upper()}] {evt.get('message', '')}"
                elif tipo == "JS_ERROR":
                    msg = f"[BROWSER][JS_ERROR] {evt.get('message', '')} @ {evt.get('source', '')}:{evt.get('line', '')}"
                elif tipo == "PROMISE_ERROR":
                    msg = f"[BROWSER][PROMISE_FAIL] {evt.get('message', '')}"
                elif tipo == "HTTP_ERROR":
                    msg = f"[BROWSER][HTTP_{evt.get('status', '???')}] {evt.get('method', '')} {evt.get('url', '')}"
                elif tipo == "NETWORK_ERROR":
                    msg = f"[BROWSER][NET_FAIL] {evt.get('method', '')} {evt.get('url', '')} — {evt.get('message', '')}"
                else:
                    msg = f"[BROWSER][{tipo}] {evt}"

                if context:
                    msg = f"[{context}] {msg}"

                # Nivel de log según tipo
                if tipo in ("JS_ERROR", "NETWORK_ERROR", "PROMISE_ERROR") or (tipo == "HTTP_ERROR" and evt.get("status", 0) >= 500):
                    log.error(msg)
                elif tipo == "HTTP_ERROR" or (tipo == "CONSOLE" and level == "warn"):
                    log.warning(msg)
                else:
                    log.debug(msg)

            return events
        except Exception:
            return []

    # ═══════════════════════════════════════════════════════════════════
    # DETECCIÓN DE ESTADO (Idéntico al bot original)
    # ═══════════════════════════════════════════════════════════════════

    def _detectar_estado(self, driver: Driver) -> str:
        """Retorna: 'tabla', 'no_encontrado', 'verificacion_fallida', 'verificacion', 'nada', 'cargando'"""
        try:
            return driver.run_js("""
                // Tabla con resultados
                var tabla = document.querySelector('table.custom-table');
                if (tabla && tabla.querySelectorAll('tbody tr.ng-star-inserted').length > 0)
                    return 'tabla';

                // Swal dialogs
                var swal = document.querySelector('.swal2-html-container');
                if (swal) {
                    var txt = (swal.innerText || '').toLowerCase();
                    if (txt.includes('no se encontraron')) return 'no_encontrado';
                    if (txt.includes('verificaci') && txt.includes('fallid')) return 'verificacion_fallida';
                    if (txt.includes('verificaci') || txt.includes('seguridad')) return 'verificacion';
                }

                // Checkbox sin marcar o iframe turnstile visible
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

                // Página cargada pero sin resultado
                var input = document.querySelector('input[formcontrolname="dni"]') ||
                            document.querySelector('input[type="text"]');
                if (input) {
                    var spinner = document.querySelector('.p-progress-spinner, .loading, .spinner');
                    if (!spinner) return 'nada';
                }

                return 'cargando';
            """)
        except Exception:
            return 'cargando'

    # ═══════════════════════════════════════════════════════════════════
    # ACCIONES (Idénticas al bot original)
    # ═══════════════════════════════════════════════════════════════════

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
        """Intenta clickear el checkbox de verificación (lógica del bot original)."""
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
                log.info(f"[CHECK] Click: {clicked}")
                return True
        except Exception:
            pass

        # Fallback: Selenium click
        try:
            cb = driver.select('input[type="checkbox"]', wait=2)
            if cb:
                cb.click()
                log.info("[CHECK] Click Selenium fallback")
                return True
        except Exception:
            pass

        return False

    def _captcha_esta_completado(self, driver: Driver) -> bool:
        """
        Verificación ESTRICTA: retorna True SOLO si el captcha/Turnstile
        está claramente completado (checkbox marcado, sin challenge visible).
        """
        try:
            return driver.run_js("""
                // 1. ¿Hay algún checkbox SIN marcar? → NO completado
                var cbs = document.querySelectorAll('input[type="checkbox"]');
                for (var i = 0; i < cbs.length; i++) {
                    if (!cbs[i].checked) {
                        var r = cbs[i].getBoundingClientRect();
                        var p = (cbs[i].closest('label') || cbs[i].parentElement);
                        var pr = p ? p.getBoundingClientRect() : r;
                        if (r.width > 0 || r.height > 0 || pr.width > 0 || pr.height > 0)
                            return false;  // Hay checkbox visible sin marcar
                    }
                }

                // 2. ¿Hay iframe de Turnstile/challenges visible? → NO completado
                var iframes = document.querySelectorAll('iframe');
                for (var i = 0; i < iframes.length; i++) {
                    var src = iframes[i].src || '';
                    if (src.includes('turnstile') || src.includes('challenges')) {
                        var r = iframes[i].getBoundingClientRect();
                        if (r.width > 0 && r.height > 0) return false;
                    }
                }

                // 3. ¿Hay swal de verificación? → NO completado
                var swal = document.querySelector('.swal2-html-container');
                if (swal) {
                    var txt = (swal.innerText || '').toLowerCase();
                    if (txt.includes('verificaci') || txt.includes('seguridad'))
                        return false;
                }

                // 4. ¿Existe el input de DNI? → Página cargada, captcha pasado
                var input = document.querySelector('input[formcontrolname="dni"]') ||
                            document.querySelector('input[type="text"]');
                if (!input) return false;  // Página ni cargó

                // Si hay checkbox y TODOS están marcados → completado
                if (cbs.length > 0) {
                    for (var i = 0; i < cbs.length; i++) {
                        if (!cbs[i].checked) return false;
                    }
                    return true;
                }

                // No hay checkbox visible y no hay challenge → asumimos completado
                return true;
            """) or False
        except Exception:
            return False

    def _verificar_captcha_estricto(self, driver: Driver, max_intentos: int = 5) -> bool:
        """
        Verificación ESTRICTA del captcha con hasta N intentos.
        Si el captcha no está completado:
          1. Intenta click en checkbox
          2. Espera 4 segundos
          3. Verifica si pasó
          4. Si no → F5 + 4s y reintentar
        Retorna True si el captcha está verificado, False si agotó intentos.
        """
        for i in range(1, max_intentos + 1):
            # Verificar si ya está completado
            if self._captcha_esta_completado(driver):
                log.info(f"[CAPTCHA] ✅ Verificación completada (intento {i}/{max_intentos})")
                return True

            log.warning(f"[CAPTCHA] ⏳ No completado, intento {i}/{max_intentos}")

            # Detectar estado actual
            estado = self._detectar_estado(driver)

            if estado == 'verificacion_fallida':
                log.warning("[CAPTCHA] ❌ Verificación fallida → F5 + 4s")
                self._cerrar_swal(driver)
                self._forzar_refresh(driver)
                continue

            if estado == 'verificacion':
                log.info("[CAPTCHA] Intentando click en checkbox...")
                self._cerrar_swal(driver)
                time.sleep(0.5)
                self._click_checkbox(driver)
                time.sleep(4)  # Esperar 4 segundos para que se procese

                # Re-verificar
                if self._captcha_esta_completado(driver):
                    log.info(f"[CAPTCHA] ✅ Verificación completada tras click (intento {i})")
                    return True
                else:
                    log.warning("[CAPTCHA] ❌ Click no resolvió → F5 + 4s")
                    self._cerrar_swal(driver)
                    self._forzar_refresh(driver)
                    continue

            if estado in ('cargando', 'nada'):
                # Página no terminó de cargar o no muestra nada → F5
                log.warning(f"[CAPTCHA] Estado '{estado}' → F5 + 4s")
                self._forzar_refresh(driver)
                continue

            # Si detectó 'tabla' o 'no_encontrado' aquí, algo raro
            # pero podría ser resultado de búsqueda anterior
            if estado in ('tabla', 'no_encontrado'):
                self._cerrar_swal(driver)
                # Limpiar resultado anterior y re-verificar
                log.info(f"[CAPTCHA] Estado '{estado}' pre-búsqueda, cerrando swal...")
                time.sleep(1)
                if self._captcha_esta_completado(driver):
                    return True

        log.error(f"[CAPTCHA] ❌ No se pudo verificar tras {max_intentos} intentos")
        return False

    def _buscar_dni(self, driver: Driver, dni: str) -> bool:
        """Ingresa DNI y click en Buscar. Retorna True si ambos OK."""
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
            log.error("[DNI] Campo no encontrado")
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
        if not btn_ok:
            log.error("[BUSCAR] Botón no encontrado")
            return False

        log.info(f"[OK] DNI {dni} buscado")
        return True

    def _esperar_resultado(self, driver: Driver, timeout: int = 15) -> str:
        """Espera resultado post-búsqueda. Retorna estado final."""
        inicio = time.time()
        while time.time() - inicio < timeout:
            estado = self._detectar_estado(driver)
            if estado not in ('cargando', 'nada'):
                return estado
            # Si lleva más de 8 segundos en 'nada', retornar
            if estado == 'nada' and (time.time() - inicio) > 8:
                return 'nada'
            time.sleep(0.5)
        return 'timeout'

    def _forzar_refresh(self, driver: Driver):
        """Fuerza la recarga de la página y espera 4 segundos."""
        log.info("[F5] Forzando recarga, esperando 4 segundos...")
        try:
            driver.run_js("location.reload(true);")
        except Exception:
            try:
                driver.get(self.URL)
                self._primera_carga = False
            except Exception:
                pass
        time.sleep(4)
        # Re-inyectar monitor si no es CDP
        if not self._cdp_configured:
            self._inject_monitor_fallback(driver)

    # ═══════════════════════════════════════════════════════════════════
    # EXTRACCIÓN DE DATOS (Idéntica al bot original)
    # ═══════════════════════════════════════════════════════════════════

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
            log.info(f"[OK] {len(data)} registro(s)")
            for idx, f in enumerate(data, 1):
                m = re.search(r'(\d{7,8})', f.get('d', ''))
                r = {
                    "dni": m.group(1) if m else dni,
                    "nombres": f.get("n", "").strip(),
                    "grado_o_titulo": f.get("g", "").strip(),
                    "institucion": f.get("i", "").strip(),
                    "fecha_diploma": f.get("fd", ""),
                    "fecha_consulta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                log.info(f"  [{idx}] {r['nombres']} | {r['grado_o_titulo'][:50]}")
                registros.append(r)
            return registros
        except Exception as e:
            log.error(f"[EXTRACT] Error: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════════
    # MÉTODO PRINCIPAL — Lógica EXACTA del bot original
    # ═══════════════════════════════════════════════════════════════════

    def procesar_dni(self, driver: Driver, dni: str) -> Dict[str, Any]:
        """
        Flujo (idéntico a sunedu_botasaurus.py):
        1. Cargar página (6s primera vez, 4s en reintentos)
        2. Verificación: si falla → F5 + 4s y REINTENTAR MISMO DNI
        3. Buscar DNI → esperar resultado
        4. Si tabla → extraer datos
        5. Si no_encontrado → cerrar, esperar 4s, retornar
        6. Si verificación fallida / nada / timeout → F5 + 4s y REINTENTAR
        7. Máximo N intentos por DNI
        """
        intento = 0

        while intento < SUNEDU_MAX_RETRIES:
            intento += 1
            log.info(f"{'='*50}")
            log.info(f"DNI: {dni} | Intento {intento}/{SUNEDU_MAX_RETRIES}")
            log.info(f"{'='*50}")

            try:
                # === CARGAR PÁGINA ===
                if self._primera_carga:
                    log.info("[CARGA] Primera carga, esperando 6 segundos...")
                    driver.get(self.URL)
                    time.sleep(6)
                    self._primera_carga = False
                    # Configurar monitoreo CDP (solo una vez)
                    self._setup_cdp_monitoring(driver)
                    # Inyectar fallback si CDP no funcionó
                    if not self._cdp_configured:
                        self._inject_monitor_fallback(driver)
                elif intento > 1:
                    self._forzar_refresh(driver)
                # else: intento 1 pero no es primera carga → página ya cargada

                # Recoger eventos del navegador
                self._collect_events(driver, f"DNI={dni} PRE_SEARCH")

                # === VERIFICACIÓN ESTRICTA PRE-BÚSQUEDA ===
                # Intenta hasta 5 veces pasar el captcha antes de buscar
                if not self._verificar_captcha_estricto(driver, max_intentos=5):
                    log.error("[CAPTCHA] No se pudo superar la verificación → reintentar")
                    self._forzar_refresh(driver)
                    continue

                # === BUSCAR DNI (solo si captcha verificado) ===
                if not self._buscar_dni(driver, dni):
                    log.warning("[BUSCAR] No se pudo buscar → F5 + 4s y reintentar")
                    self._forzar_refresh(driver)
                    continue

                time.sleep(1)  # Pequeña espera post-búsqueda

                # === ESPERAR RESULTADO ===
                resultado = self._esperar_resultado(driver, timeout=15)
                log.info(f"[RESULTADO] Estado: {resultado}")

                # Recoger eventos del navegador post-búsqueda
                self._collect_events(driver, f"DNI={dni} POST_SEARCH")

                # === TABLA CON RESULTADOS ===
                if resultado == 'tabla':
                    registros = self._extraer_datos(driver, dni)
                    if registros:
                        log.info("[ESPERA] Resultados encontrados, esperando 4 segundos...")
                        time.sleep(4)
                        return {"encontrado": True, "datos": registros, "motivo": "Encontrado"}
                    # Tabla presente pero sin datos
                    return {"encontrado": False, "datos": None, "motivo": Motivo.NO_ENCONTRADO}

                # === NO ENCONTRADO ===
                elif resultado == 'no_encontrado':
                    self._cerrar_swal(driver)
                    log.info(f"[--] DNI {dni}: No se encontraron resultados")
                    log.info("[ESPERA] Esperando 4 segundos antes del siguiente DNI...")
                    time.sleep(4)
                    return {"encontrado": False, "datos": None, "motivo": Motivo.NO_ENCONTRADO}

                # === VERIFICACIÓN FALLIDA POST-BÚSQUEDA ===
                elif resultado == 'verificacion_fallida':
                    log.warning("[VERIF] Verificación fallida post-búsqueda → F5 + 4s y reintentar")
                    self._cerrar_swal(driver)
                    self._forzar_refresh(driver)
                    continue

                # === VERIFICACIÓN POST-BÚSQUEDA ===
                elif resultado == 'verificacion':
                    log.warning("[VERIF] Verificación post-búsqueda detectada")
                    self._cerrar_swal(driver)
                    time.sleep(0.5)
                    self._click_checkbox(driver)
                    time.sleep(2)

                    # Revisar estado después de intentar resolver
                    post_estado = self._detectar_estado(driver)
                    if post_estado == 'tabla':
                        registros = self._extraer_datos(driver, dni)
                        if registros:
                            time.sleep(4)
                            return {"encontrado": True, "datos": registros, "motivo": "Encontrado"}
                        return {"encontrado": False, "datos": None, "motivo": Motivo.NO_ENCONTRADO}
                    elif post_estado == 'no_encontrado':
                        self._cerrar_swal(driver)
                        log.info(f"[--] DNI {dni}: No se encontraron resultados")
                        time.sleep(4)
                        return {"encontrado": False, "datos": None, "motivo": Motivo.NO_ENCONTRADO}
                    else:
                        log.warning("[VERIF] No superada post-búsqueda → F5 + 4s y reintentar mismo DNI")
                        self._cerrar_swal(driver)
                        self._forzar_refresh(driver)
                        continue

                # === NADA APARECIÓ ===
                elif resultado == 'nada':
                    log.warning("[NADA] No apareció ningún mensaje ni resultado → F5 + 4s y reintentar")
                    self._collect_events(driver, f"DNI={dni} NADA")
                    self._forzar_refresh(driver)
                    continue

                # === TIMEOUT ===
                elif resultado == 'timeout':
                    log.warning("[TIMEOUT] Sin respuesta de la página → F5 + 4s y reintentar")
                    self._collect_events(driver, f"DNI={dni} TIMEOUT")
                    self._forzar_refresh(driver)
                    continue

            except Exception as e:
                log.error(f"[!] Error: {repr(e)} → F5 + 4s y reintentar")
                self._collect_events(driver, f"DNI={dni} EXCEPTION")
                self._forzar_refresh(driver)

        # Agotados los intentos
        raise RuntimeError(f"{Motivo.MAX_REINTENTOS} ({SUNEDU_MAX_RETRIES} intentos)")

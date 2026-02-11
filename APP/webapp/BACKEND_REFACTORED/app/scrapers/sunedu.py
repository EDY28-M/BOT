
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

    window.onerror = function(message, source, lineno, colno, error) {
        pushEvent({
            type: 'JS_ERROR',
            message: String(message),
            source: String(source || ''),
            line: lineno,
            stack: error ? String(error.stack || '').substring(0, 300) : ''
        });
    };

    window.addEventListener('unhandledrejection', function(event) {
        pushEvent({
            type: 'PROMISE_ERROR',
            message: event.reason ? String(event.reason.message || event.reason).substring(0, 300) : 'unknown'
        });
    });

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

    var originalFetch = window.fetch;
    window.fetch = function() {
        var url = arguments[0];
        var opts = arguments[1] || {};
        var method = opts.method || 'GET';
        return originalFetch.apply(this, arguments).then(function(response) {
            if (!response.ok) {
                pushEvent({ type: 'HTTP_ERROR', url: String(url).substring(0, 200), status: response.status, method: method });
            }
            return response;
        }).catch(function(err) {
            pushEvent({ type: 'NETWORK_ERROR', url: String(url).substring(0, 200), method: method, message: String(err.message).substring(0, 200) });
            throw err;
        });
    };

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
    VERIFICACION_FALLIDA = "Verificación fallida en SUNEDU - se refrescó la página"
    NADA_APARECIO = "No apareció ningún resultado ni mensaje en SUNEDU"
    BOTON_NO_ENCONTRADO = "No se encontró el botón de búsqueda en SUNEDU"
    PAGINA_NO_CARGO = "La página de SUNEDU no cargó correctamente"
    ERROR_EXTRACCION = "Error al extraer datos de la tabla SUNEDU"
    TIMEOUT = "Tiempo de espera agotado"
    MAX_REINTENTOS = "Se agotaron todos los reintentos en SUNEDU"


class SuneduScraper:
    """
    Scraper SUNEDU — COPIA EXACTA del bot original (workers.py SuneduLogic)
    + monitoreo CDP profesional.

    Método _pasar_verificacion() portado directamente del bot que funciona.
    """

    URL = SUNEDU_URL

    def __init__(self):
        self._primera_carga = True
        self._cdp_configured = False

    # ═══════════════════════════════════════════════════════════════════
    # MONITOREO CDP
    # ═══════════════════════════════════════════════════════════════════

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
                log.info("[MONITOR] ✅ CDP monitoring activo")
                return
        except Exception as e:
            log.warning(f"[MONITOR] CDP no disponible ({e}), usando fallback")
        self._inject_monitor_fallback(driver)

    def _inject_monitor_fallback(self, driver: Driver):
        try:
            driver.run_js(MONITOR_INIT_SCRIPT)
        except Exception:
            pass

    def _collect_events(self, driver: Driver, context: str = ""):
        try:
            events = driver.run_js("""
                var evts = window.__capturedEvents || [];
                window.__capturedEvents = [];
                return evts;
            """)
            if not events:
                return
            for evt in events:
                tipo = evt.get("type", "UNKNOWN")
                level = evt.get("level", "")
                if tipo == "CONSOLE":
                    msg = f"[BROWSER][CONSOLE.{level.upper()}] {evt.get('message', '')}"
                elif tipo == "JS_ERROR":
                    msg = f"[BROWSER][JS_ERROR] {evt.get('message', '')} @ {evt.get('source', '')}:{evt.get('line', '')}"
                elif tipo == "HTTP_ERROR":
                    msg = f"[BROWSER][HTTP_{evt.get('status', '???')}] {evt.get('method', '')} {evt.get('url', '')}"
                elif tipo == "NETWORK_ERROR":
                    msg = f"[BROWSER][NET_FAIL] {evt.get('method', '')} {evt.get('url', '')} — {evt.get('message', '')}"
                else:
                    msg = f"[BROWSER][{tipo}] {evt}"
                if context:
                    msg = f"[{context}] {msg}"
                if tipo in ("JS_ERROR", "NETWORK_ERROR", "PROMISE_ERROR") or (tipo == "HTTP_ERROR" and evt.get("status", 0) >= 500):
                    log.error(msg)
                elif tipo == "HTTP_ERROR" or (tipo == "CONSOLE" and level == "warn"):
                    log.warning(msg)
                else:
                    log.debug(msg)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════
    # DETECCIÓN DE ESTADO — Idéntico al bot original
    # ═══════════════════════════════════════════════════════════════════

    def detectar_estado(self, driver: Driver) -> str:
        """Retorna: 'tabla', 'no_encontrado', 'verificacion_fallida', 'verificacion', 'nada', 'cargando'"""
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
    # ACCIONES — Idénticas al bot original
    # ═══════════════════════════════════════════════════════════════════

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
        """Intenta clickear el checkbox de verificación."""
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

    def buscar_dni(self, driver: Driver, dni: str) -> bool:
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

    def esperar_resultado(self, driver: Driver, timeout: int = 15) -> str:
        """Espera resultado post-búsqueda."""
        inicio = time.time()
        while time.time() - inicio < timeout:
            estado = self.detectar_estado(driver)
            if estado not in ('cargando', 'nada'):
                return estado
            if estado == 'nada' and (time.time() - inicio) > 8:
                return 'nada'
            time.sleep(0.5)
        return 'timeout'

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
    # _pasar_verificacion — COPIA EXACTA del bot original (workers.py)
    # ═══════════════════════════════════════════════════════════════════

    def _pasar_verificacion(self, driver: Driver, espera_extra: bool = False) -> bool:
        """
        Detecta y supera la verificación de Turnstile/checkbox.
        espera_extra: True si la página fue recién cargada/recargada.
        Retorna True si la verificación fue superada o no era necesaria.

        PORTADO DIRECTAMENTE de workers.py SuneduLogic._pasar_verificacion()
        """
        estado = self.detectar_estado(driver)
        log.info(f"[VERIF] Estado inicial: {estado}")

        # Limpiar resultados viejos de un DNI anterior
        if estado in ("tabla", "no_encontrado"):
            self.cerrar_swal(driver)
            time.sleep(0.5)
            estado = self.detectar_estado(driver)
            log.info(f"[VERIF] Estado post-limpieza: {estado}")

        # Si la página es fresca, dar tiempo extra para que cargue Turnstile
        if espera_extra and estado in ("cargando", "nada"):
            log.info("[VERIF] Página fresca, esperando 2s extra para Turnstile...")
            time.sleep(2)
            estado = self.detectar_estado(driver)
            log.info(f"[VERIF] Estado post-espera: {estado}")

        # Verificación fallida explícita → no se puede superar, necesita F5
        if estado == "verificacion_fallida":
            log.warning("[VERIF] ❌ Verificación fallida explícita")
            self.cerrar_swal(driver)
            return False

        # No hay verificación → OK, puede buscar
        if estado != "verificacion":
            log.info(f"[VERIF] ✅ No requiere verificación (estado: {estado})")
            return True

        # Intentar pasar la verificación (hasta 3 intentos)
        for attempt in range(3):
            log.info(f"[VERIF] Intento {attempt + 1}/3 de resolver verificación...")
            self.cerrar_swal(driver)
            time.sleep(0.5)
            self.click_checkbox(driver)
            time.sleep(3)

            post = self.detectar_estado(driver)
            log.info(f"[VERIF] Estado post-click: {post}")

            if post == "verificacion_fallida":
                log.warning("[VERIF] ❌ Verificación fallida post-click")
                self.cerrar_swal(driver)
                return False

            if post != "verificacion":
                log.info(f"[VERIF] ✅ Verificación superada (estado: {post})")
                time.sleep(1)
                return True

            log.warning(f"[VERIF] ⏳ Intento {attempt + 1}/3 no resolvió")

        log.error("[VERIF] ❌ No se pudo superar tras 3 intentos")
        return False

    def _recargar_pagina(self, driver: Driver):
        """Recarga la página y espera 4 segundos."""
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
    # MÉTODO PRINCIPAL — COPIA EXACTA del bot original (workers.py)
    # ═══════════════════════════════════════════════════════════════════

    def procesar_dni(self, driver: Driver, dni: str) -> Dict[str, Any]:
        """
        PORTADO DIRECTAMENTE de workers.py SuneduLogic.procesar_un_dni()

        Flujo:
        1. Preparar página (primera carga 6s, reintentos F5+4s, mismo sesión cerrar swal)
        2. _pasar_verificacion() → si falla → F5 + 4s + reintentar MISMO DNI
        3. Buscar DNI → esperar resultado
        4. tabla → extraer
        5. no_encontrado → retornar
        6. verificacion/verificacion_fallida/nada/timeout → F5 + 4s + reintentar
        7. Máximo SUNEDU_MAX_RETRIES intentos
        """
        ultimo_motivo = Motivo.MAX_REINTENTOS

        for intento in range(1, SUNEDU_MAX_RETRIES + 1):
            log.info(f"{'='*50}")
            log.info(f"DNI: {dni} | Intento {intento}/{SUNEDU_MAX_RETRIES}")
            log.info(f"{'='*50}")

            try:
                # ── Preparar página ──
                pagina_fresca = False

                if self._primera_carga:
                    log.info("[CARGA] Primera carga...")
                    driver.get(self.URL)
                    time.sleep(6)
                    self._primera_carga = False
                    pagina_fresca = True
                    # CDP monitoring
                    self._setup_cdp_monitoring(driver)
                    if not self._cdp_configured:
                        self._inject_monitor_fallback(driver)
                elif intento > 1:
                    log.info("[F5] Refrescando página...")
                    self._recargar_pagina(driver)
                    pagina_fresca = True
                else:
                    # Nuevo DNI, misma sesión → limpiar estado anterior
                    self.cerrar_swal(driver)
                    time.sleep(0.3)

                # Recoger eventos
                self._collect_events(driver, f"DNI={dni} PRE")

                # ── Verificación de seguridad (Turnstile) ──
                if not self._pasar_verificacion(driver, espera_extra=pagina_fresca):
                    log.warning("[VERIF] Verificación no superada → refrescando")
                    ultimo_motivo = Motivo.VERIFICACION_NO_SUPERADA
                    self._recargar_pagina(driver)
                    continue

                # ── Buscar DNI ──
                if not self.buscar_dni(driver, dni):
                    log.warning("[BUSCAR] Botón no encontrado → refrescando")
                    ultimo_motivo = Motivo.BOTON_NO_ENCONTRADO
                    self._recargar_pagina(driver)
                    continue

                time.sleep(0.8)

                # Esperar resultado
                resultado = self.esperar_resultado(driver, timeout=15)
                log.info(f"[RESULTADO] {resultado}")

                # Recoger eventos post-búsqueda
                self._collect_events(driver, f"DNI={dni} POST")

                if resultado == "tabla":
                    datos = self.extraer_datos(driver, dni)
                    if datos:
                        time.sleep(4)  # Espera anti-ban
                        return {"encontrado": True, "datos": datos, "motivo": "Encontrado en SUNEDU"}
                    return {"encontrado": False, "datos": None, "motivo": Motivo.ERROR_EXTRACCION}

                elif resultado == "no_encontrado":
                    self.cerrar_swal(driver)
                    log.info(f"[--] DNI {dni}: No encontrado")
                    time.sleep(4)  # Espera anti-ban
                    return {"encontrado": False, "datos": None, "motivo": Motivo.NO_ENCONTRADO}

                elif resultado == "verificacion_fallida":
                    log.warning("[VERIF] Verificación fallida post-búsqueda → F5 + 4s")
                    self.cerrar_swal(driver)
                    ultimo_motivo = Motivo.CAPTCHA_FALLO
                    self._recargar_pagina(driver)
                    continue

                elif resultado == "verificacion":
                    log.warning("[VERIF] Verificación post-búsqueda")
                    self.cerrar_swal(driver)
                    time.sleep(0.5)
                    self.click_checkbox(driver)
                    time.sleep(3)

                    post = self.detectar_estado(driver)
                    log.info(f"[VERIF] Post-click estado: {post}")

                    if post == "tabla":
                        datos = self.extraer_datos(driver, dni)
                        if datos:
                            time.sleep(4)
                            return {"encontrado": True, "datos": datos, "motivo": "Encontrado en SUNEDU"}
                        return {"encontrado": False, "datos": None, "motivo": Motivo.ERROR_EXTRACCION}

                    elif post == "no_encontrado":
                        self.cerrar_swal(driver)
                        time.sleep(4)
                        return {"encontrado": False, "datos": None, "motivo": Motivo.NO_ENCONTRADO}

                    else:
                        log.warning("[VERIF] No superada post-búsqueda → F5 + 4s")
                        self.cerrar_swal(driver)
                        ultimo_motivo = Motivo.VERIFICACION_NO_SUPERADA
                        self._recargar_pagina(driver)
                        continue

                elif resultado == "nada":
                    log.warning("[NADA] Sin resultado ni mensaje → F5 + 4s")
                    self._collect_events(driver, f"DNI={dni} NADA")
                    ultimo_motivo = Motivo.NADA_APARECIO
                    self._recargar_pagina(driver)
                    continue

                elif resultado == "timeout":
                    log.warning("[TIMEOUT] Sin respuesta → F5 + 4s")
                    self._collect_events(driver, f"DNI={dni} TIMEOUT")
                    ultimo_motivo = Motivo.TIMEOUT
                    self._recargar_pagina(driver)
                    continue

            except Exception as e:
                log.error(f"[!] Error: {repr(e)} → F5 + 4s")
                self._collect_events(driver, f"DNI={dni} EXCEPTION")
                ultimo_motivo = f"{Motivo.PAGINA_NO_CARGO}: {str(e)[:200]}"
                self._recargar_pagina(driver)

        # Agotados reintentos
        raise RuntimeError(f"{ultimo_motivo} ({SUNEDU_MAX_RETRIES} intentos)")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUNEDU BOT - Versión Botasaurus
Consulta masiva de grados y títulos por DNI.
Estrategia: si la verificación no se supera → refrescar página y reintentar mismo DNI.
"""

import sys
import time
import random
import re
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List

try:
    from botasaurus.browser import browser, Driver
    BOTASAURUS_AVAILABLE = True
except ImportError:
    BOTASAURUS_AVAILABLE = False
    print("[!] Botasaurus no instalado. Ejecuta: pip install botasaurus")
    sys.exit(1)

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("SUNEDU")


@dataclass
class Registro:
    dni: str
    nombres: str = ""
    grado_o_titulo: str = ""
    institucion: str = ""
    fecha_diploma: str = ""
    fecha_consulta: str = ""
    estado: str = "PENDIENTE"


class SuneduBotasaurus:
    URL = "https://constanciasweb.sunedu.gob.pe/#/modulos/grados-y-titulos"

    def __init__(self):
        self.output_dir = Path("resultados")
        self.output_dir.mkdir(exist_ok=True)
        self.resultados: List[Registro] = []
        self._primera_carga = True  # Flag para saber si es la primera vez

    # ─── Estado de la página ──────────────────────────────────────────

    def detectar_estado(self, driver: Driver) -> str:
        """Retorna: 'tabla', 'no_encontrado', 'verificacion', 'cargando'"""
        try:
            return driver.run_js("""
                // Tabla con resultados
                var tabla = document.querySelector('table.custom-table');
                if (tabla && tabla.querySelectorAll('tbody tr.ng-star-inserted').length > 0)
                    return 'tabla';

                // Swal "no se encontraron resultados"
                var swal = document.querySelector('.swal2-html-container');
                if (swal) {
                    var txt = (swal.innerText || '').toLowerCase();
                    if (txt.includes('no se encontraron')) return 'no_encontrado';
                    if (txt.includes('verificaci') || txt.includes('seguridad')) return 'verificacion';
                }

                // Checkbox sin marcar o iframe de turnstile visible
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
        except:
            return 'cargando'

    # ─── Cerrar diálogo swal ──────────────────────────────────────────

    def cerrar_swal(self, driver: Driver):
        try:
            driver.run_js("""
                var btn = document.querySelector('button.swal2-close') ||
                          document.querySelector('button[aria-label="Close this dialog"]');
                if (btn) btn.click();
            """)
        except:
            pass

    # ─── Click en checkbox ────────────────────────────────────────────

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
        except:
            pass

        # Fallback: Selenium click
        try:
            cb = driver.select('input[type="checkbox"]', wait=2)
            if cb:
                cb.click()
                log.info("[CHECK] Click Selenium")
                return True
        except:
            pass

        return False

    # ─── Ingresar DNI y Buscar (rápido: 1 segundo) ─────────────────────

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

        time.sleep(0.5)  # Pequeña pausa antes de buscar

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

    # ─── Esperar resultado ────────────────────────────────────────────

    def esperar_resultado(self, driver: Driver, timeout: int = 15) -> str:
        """Espera resultado post-búsqueda.
        Retorna: 'tabla', 'no_encontrado', 'verificacion', 'timeout'"""
        inicio = time.time()
        while time.time() - inicio < timeout:
            estado = self.detectar_estado(driver)
            if estado != 'cargando':
                return estado
            time.sleep(0.5)
        return 'timeout'

    # ─── Extraer datos ────────────────────────────────────────────────

    def extraer_datos(self, driver: Driver, dni: str) -> List[Registro]:
        try:
            data = driver.run_js("""
                var res = [];
                var tabla = document.querySelector('table.custom-table');
                if (!tabla) return res;
                var filas = tabla.querySelectorAll('tbody tr.ng-star-inserted');
                filas.forEach(function(fila) {
                    var celdas = fila.querySelectorAll('td');
                    if (celdas.length < 3) return;
                    // Graduado
                    var ps1 = celdas[0].querySelectorAll('p');
                    var nombre = '', dniT = '';
                    for (var i = 0; i < ps1.length; i++) {
                        var t = ps1[i].textContent.trim();
                        if (t.includes('DNI')) dniT = t;
                        else if (t.length > 3 && t.includes(',')) nombre = t;
                    }
                    // Grado y fecha diploma
                    var ps2 = celdas[1].querySelectorAll('p');
                    var grado = '', fDip = '';
                    for (var i = 0; i < ps2.length; i++) {
                        var t = ps2[i].textContent.trim(), tl = t.toLowerCase();
                        if (tl.includes('fecha de diploma:')) fDip = t.split(':').slice(1).join(':').trim();
                        else if (t.length > 5 && !tl.startsWith('grado') && !tl.startsWith('fecha') && !grado) grado = t;
                    }
                    // Institución
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
                r = Registro(
                    dni=m.group(1) if m else dni,
                    nombres=f.get('n', '').strip(),
                    grado_o_titulo=f.get('g', '').strip(),
                    institucion=f.get('i', '').strip(),
                    fecha_diploma=f.get('fd', ''),
                    fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    estado="ENCONTRADO"
                )
                log.info(f"  [{idx}] {r.nombres} | {r.grado_o_titulo[:50]}")
                registros.append(r)
            return registros
        except Exception as e:
            log.error(f"[EXTRACT] Error: {e}")
            return []

    # ─── Consulta de un DNI ───────────────────────────────────────────

    def consultar_dni(self, driver: Driver, dni: str) -> List[Registro]:
        """
        Flujo:
        1. Cargar página (6s primera vez, 4s en reintentos)
        2. Verificación: si falla → refresh y REINTENTAR MISMO DNI
        3. Buscar DNI → esperar resultado
        4. Si tabla → extraer datos
        5. Si no_encontrado → cerrar, esperar 4s, retornar vacío para siguiente DNI
        6. Si verificación post-búsqueda → refresh y REINTENTAR MISMO DNI
        """
        max_intentos = 5
        intento = 0
        
        while intento < max_intentos:
            intento += 1
            log.info(f"{'='*50}")
            log.info(f"DNI: {dni} | Intento {intento}/{max_intentos}")
            log.info(f"{'='*50}")

            try:
                # === CARGAR PÁGINA ===
                if self._primera_carga:
                    # Primera vez: abrir URL y esperar 6 segundos
                    log.info("[CARGA] Primera carga, esperando 6 segundos...")
                    driver.get(self.URL)
                    time.sleep(6)
                    self._primera_carga = False
                elif intento > 1:
                    # Reintentos por verificación fallida: refresh y esperar 6 segundos
                    log.info("[F5] Refrescando página, esperando 6 segundos...")
                    driver.run_js("location.reload(true);")
                    time.sleep(6)
                # else: intento 1 pero no es primera carga (ya está cargada)

                # === VERIFICACIÓN PRE-BÚSQUEDA ===
                estado = self.detectar_estado(driver)
                if estado == 'verificacion':
                    log.info("[VERIF] Verificación detectada, intentando resolver...")
                    self.cerrar_swal(driver)
                    time.sleep(0.5)
                    self.click_checkbox(driver)
                    time.sleep(2)
                    
                    # Revisar si se resolvió
                    estado = self.detectar_estado(driver)
                    if estado == 'verificacion':
                        log.warning("[VERIF] No se superó → Refresh y reintentar mismo DNI")
                        continue  # Vuelve al inicio del while, mismo DNI
                    time.sleep(1)

                # === BUSCAR DNI (1 segundo) ===
                if not self.buscar_dni(driver, dni):
                    # Si no pudo buscar, esperar un poco y reintentar
                    time.sleep(2)
                    continue

                time.sleep(1)  # Pequeña espera post-búsqueda

                # === ESPERAR RESULTADO ===
                resultado = self.esperar_resultado(driver, timeout=15)

                # === TABLA CON RESULTADOS ===
                if resultado == 'tabla':
                    registros = self.extraer_datos(driver, dni)
                    if registros:
                        log.info("[ESPERA] Resultados encontrados, esperando 4 segundos...")
                        time.sleep(4)
                        return registros
                    return [self._no_encontrado(dni, "SIN DATOS")]

                # === NO ENCONTRADO ===
                elif resultado == 'no_encontrado':
                    self.cerrar_swal(driver)
                    log.info(f"[--] DNI {dni}: No se encontraron resultados")
                    log.info("[ESPERA] Esperando 4 segundos antes del siguiente DNI...")
                    time.sleep(4)
                    return [self._no_encontrado(dni, "NO ENCONTRADO")]

                # === VERIFICACIÓN POST-BÚSQUEDA ===
                elif resultado == 'verificacion':
                    log.warning("[VERIF] Verificación post-búsqueda detectada")
                    self.cerrar_swal(driver)
                    time.sleep(0.5)
                    self.click_checkbox(driver)
                    time.sleep(2)
                    
                    # Revisar estado después de intentar resolver
                    post_estado = self.detectar_estado(driver)
                    if post_estado == 'tabla':
                        registros = self.extraer_datos(driver, dni)
                        if registros:
                            return registros
                        return [self._no_encontrado(dni, "SIN DATOS")]
                    elif post_estado == 'no_encontrado':
                        self.cerrar_swal(driver)
                        log.info(f"[--] DNI {dni}: No se encontraron resultados")
                        time.sleep(4)
                        return [self._no_encontrado(dni, "NO ENCONTRADO")]
                    else:
                        # Verificación no resuelta → refresh y reintentar MISMO DNI
                        log.warning("[VERIF] No superada post-búsqueda → Refresh y reintentar mismo DNI")
                        continue  # Vuelve al inicio del while, mismo DNI

                # === TIMEOUT ===
                elif resultado == 'timeout':
                    log.warning("[TIMEOUT] Esperando resultado → Refresh y reintentar")
                    continue  # Vuelve al inicio del while, mismo DNI

            except Exception as e:
                log.error(f"[!] Error: {e}")
                time.sleep(2)

        # Agotados los intentos
        log.error(f"[X] DNI {dni}: Sin resultado tras {max_intentos} intentos")
        return [self._no_encontrado(dni, "ERROR")]

    def _no_encontrado(self, dni: str, estado: str) -> Registro:
        return Registro(
            dni=dni, nombres="NO SE ENCONTRÓ", grado_o_titulo="NO SE ENCONTRÓ",
            institucion="NO SE ENCONTRÓ", estado=estado,
            fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

    # ─── Procesamiento de lista ───────────────────────────────────────

    def procesar_lista(self, archivo: str):
        dnis = self._leer_dnis(archivo)
        if not dnis:
            log.error("No se encontraron DNIs")
            return

        log.info(f"Total DNIs: {len(dnis)}")

        @browser(headless=False, block_images=True, window_size=(1366, 768))
        def ejecutar(driver: Driver, data):
            for i, dni in enumerate(data["dnis"], 1):
                registros = self.consultar_dni(driver, dni)
                self.resultados.extend(registros)

                if i % 5 == 0:
                    self._guardar(f"_progreso_{i}")

            return {"total": len(self.resultados)}

        resultado = ejecutar({"dnis": dnis})
        log.info(f"Total procesados: {resultado}")
        self._guardar("_final")

    def _leer_dnis(self, archivo: str) -> List[str]:
        path = Path(archivo)
        if not path.exists():
            log.error(f"Archivo no encontrado: {archivo}")
            return []
        try:
            if archivo.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(archivo, dtype=str)
            else:
                df = pd.read_csv(archivo, dtype=str)
            for col in df.columns:
                if col.upper() in ['DNI', 'DOCUMENTO']:
                    dnis = df[col].dropna().astype(str).str.strip().tolist()
                    dnis = [d for d in dnis if d.isdigit()]
                    return list(dict.fromkeys(dnis))
        except Exception as e:
            log.error(f"Error leyendo archivo: {e}")
        return []

    def _guardar(self, sufijo: str = ""):
        if not self.resultados:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        df = pd.DataFrame([asdict(r) for r in self.resultados])
        path = self.output_dir / f"SUNEDU_BT{sufijo}_{ts}.xlsx"
        df.to_excel(path, index=False, engine='openpyxl')
        log.info(f"[OK] Guardado: {path.name}")


def main():
    print("=" * 60)
    print("  SUNEDU BOT - Botasaurus Edition")
    print("=" * 60)

    if not BOTASAURUS_AVAILABLE:
        return

    archivo = sys.argv[1] if len(sys.argv) > 1 else "dni_lista.csv"
    SuneduBotasaurus().procesar_lista(archivo)

    print("\n[OK] PROCESO FINALIZADO")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DNI PERU BOT - Obtener nombres por DNI (FAST VERSION)
"""
import sys, time, random, logging
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

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger("DNIPERU")

@dataclass
class PersonaDNI:
    dni: str
    nombres: str = ""
    apellido_paterno: str = ""
    apellido_materno: str = ""
    nombre_completo: str = ""
    estado: str = "PENDIENTE"


class DniPeruBot:
    URL = "https://dniperu.com/buscar-dni-nombres-apellidos/"

    def __init__(self):
        self.output_dir = Path("resultados")
        self.output_dir.mkdir(exist_ok=True)
        self.resultados: List[PersonaDNI] = []

    def consultar_dni(self, driver: Driver, dni: str) -> Optional[PersonaDNI]:
        for intento in range(1, 3):
            try:
                if intento == 1:
                    driver.get(self.URL)
                else:
                    driver.run_js("location.reload(true);")
                time.sleep(1)

                # Ingresar DNI y hacer click
                driver.run_js(f"""
                    var input = document.querySelector('#dni4');
                    if (input) {{
                        input.value = '{dni}';
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                    setTimeout(function() {{
                        var btn = document.querySelector('#buscar-dni-button');
                        if (btn) btn.click();
                    }}, 200);
                """)

                time.sleep(2)

                # Esperar resultado (max 5s)
                for _ in range(5):
                    resultado = driver.run_js("""
                        var ta = document.querySelector('#resultado_dni');
                        return ta ? ta.value : null;
                    """)
                    if resultado:
                        return self._parsear(dni, resultado)
                    time.sleep(1)

            except Exception as e:
                log.error(f"Error: {e}")

        return PersonaDNI(dni=dni, estado="ERROR")

    def _parsear(self, dni: str, texto: str) -> PersonaDNI:
        nombres = ap_p = ap_m = ""
        for linea in texto.split('\n'):
            if linea.startswith("Nombres:"): nombres = linea.split(":",1)[1].strip()
            elif linea.startswith("Apellido Paterno:"): ap_p = linea.split(":",1)[1].strip()
            elif linea.startswith("Apellido Materno:"): ap_m = linea.split(":",1)[1].strip()
        return PersonaDNI(dni=dni, nombres=nombres, apellido_paterno=ap_p, apellido_materno=ap_m,
                          nombre_completo=f"{ap_p} {ap_m}, {nombres}".strip(),
                          estado="OK" if nombres else "NO")

    def procesar_lista(self, archivo: str):
        dnis = self._leer_dnis(archivo)
        if not dnis:
            log.error("No DNIs")
            return
        log.info(f"Total: {len(dnis)} DNIs")

        @browser(headless=False, block_images=True, window_size=(1200, 700))
        def ejecutar(driver: Driver, data):
            for i, dni in enumerate(data["dnis"], 1):
                log.info(f"[{i}/{len(data['dnis'])}] {dni}")
                p = self.consultar_dni(driver, dni)
                if p:
                    self.resultados.append(p)
                    log.info(f"  -> {p.nombre_completo or 'NO ENCONTRADO'}")
                if i % 10 == 0:
                    self._guardar("_prog")
                time.sleep(random.uniform(0.5, 1.5))
            return len(self.resultados)

        ejecutar({"dnis": dnis})
        self._guardar("_final")

    def _leer_dnis(self, archivo: str) -> List[str]:
        try:
            df = pd.read_excel(archivo, dtype=str) if archivo.endswith('.xlsx') else pd.read_csv(archivo, dtype=str)
            dni_col = inst_col = None
            for c in df.columns:
                if c.upper() in ['DNI','DOCUMENTO']: dni_col = c
                if 'INSTITU' in c.upper(): inst_col = c
            if not dni_col: return []
            if inst_col:
                mask = df[inst_col].str.upper().str.contains('NO SE ENCONTR', na=False)
                df = df[mask]
                log.info(f"Filtrados: {len(df)}")
            return list(dict.fromkeys(df[dni_col].dropna().astype(str).str.strip().tolist()))
        except Exception as e:
            log.error(f"Error: {e}")
            return []

    def _guardar(self, sufijo=""):
        if not self.resultados: return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        df = pd.DataFrame([asdict(r) for r in self.resultados])
        path = self.output_dir / f"NOMBRES{sufijo}_{ts}.xlsx"
        df.to_excel(path, index=False)
        log.info(f"Guardado: {path.name}")


if __name__ == "__main__":
    print("="*50)
    print("  DNI PERU BOT - FAST")
    print("="*50)
    archivo = sys.argv[1] if len(sys.argv) > 1 else "DNI_UNIVERSIDADES.xlsx"
    DniPeruBot().procesar_lista(archivo)
    print("[OK] FIN")

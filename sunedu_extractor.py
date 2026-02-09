#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUNEDU EXTRACTOR - Versión Manual/Extractor
1. Tú haces la consulta en tu navegador normal
2. Guardas la página (Ctrl+S) como HTML
3. Este script extrae los datos automáticamente

Esto evita TODOS los problemas de detección de bots.
"""

import os
import re
import pandas as pd
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List
from bs4 import BeautifulSoup


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


class SuneduExtractor:
    """Extrae datos de archivos HTML guardados de SUNEDU"""
    
    def __init__(self):
        self.resultados: List[RegistroProfesional] = []
        self.input_dir = Path("html_consultas")
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir = Path("resultados")
        self.output_dir.mkdir(exist_ok=True)
    
    def extraer_de_html(self, archivo_html: str, dni: str = "") -> List[RegistroProfesional]:
        """Extrae datos de un archivo HTML"""
        registros = []
        
        try:
            with open(archivo_html, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            
            # Buscar tabla de resultados
            tablas = soup.find_all('table')
            
            for tabla in tablas:
                filas = tabla.find_all('tr')
                
                for fila in filas:
                    celdas = fila.find_all(['td', 'th'])
                    if len(celdas) < 3:
                        continue
                    
                    # Intentar extraer datos
                    try:
                        texto_celdas = [c.get_text(strip=True) for c in celdas]
                        
                        # Buscar patrones de datos SUNEDU
                        # Celda 1: Nombre y DNI
                        nombres = ""
                        dni_encontrado = dni
                        
                        for texto in texto_celdas:
                            if "DNI" in texto and any(c.isdigit() for c in texto):
                                # Extraer DNI
                                match = re.search(r'DNI\s*(\d+)', texto)
                                if match:
                                    dni_encontrado = match.group(1)
                                # Extraer nombre
                                lineas = [l.strip() for l in texto.split('\n') if l.strip()]
                                for linea in lineas:
                                    if ',' in linea and not 'DNI' in linea:
                                        nombres = linea
                                        break
                        
                        # Celda 2: Grado/Título
                        grado_titulo = ""
                        fecha_diploma = ""
                        fecha_matricula = "Sin información"
                        fecha_egreso = "Sin información"
                        
                        for texto in texto_celdas:
                            if any(palabra in texto.upper() for palabra in ['BACHILLER', 'LICENCIADO', 'INGENIERO', 'MEDICO', 'ABOGADO', 'TITULO', 'GRADO']):
                                lineas = [l.strip() for l in texto.split('\n') if l.strip()]
                                if lineas:
                                    grado_titulo = lineas[0]
                                
                                # Buscar fechas
                                for linea in lineas:
                                    if 'diploma:' in linea.lower():
                                        fecha_diploma = linea.split(':', 1)[-1].strip()
                                    elif 'matricula:' in linea.lower():
                                        fecha_matricula = linea.split(':', 1)[-1].strip()
                                    elif 'egreso:' in linea.lower():
                                        fecha_egreso = linea.split(':', 1)[-1].strip()
                        
                        # Celda 3: Institución
                        institucion = ""
                        for texto in texto_celdas:
                            if any(palabra in texto.upper() for palabra in ['UNIVERSIDAD', 'INSTITUTO', 'ESCUELA', 'PERU']):
                                lineas = [l.strip() for l in texto.split('\n') if l.strip()]
                                if lineas:
                                    institucion = lineas[0]
                        
                        # Si encontramos datos, crear registro
                        if nombres or grado_titulo:
                            registro = RegistroProfesional(
                                dni=dni_encontrado or dni,
                                nombres=nombres,
                                grado_o_titulo=grado_titulo,
                                institucion=institucion,
                                fecha_diploma=fecha_diploma,
                                fecha_matricula=fecha_matricula,
                                fecha_egreso=fecha_egreso,
                                fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                estado="ENCONTRADO" if (nombres or grado_titulo) else "NO ENCONTRADO"
                            )
                            registros.append(registro)
                            
                    except Exception as e:
                        continue
            
            # Si no se encontraron registros estructurados, buscar texto plano
            if not registros:
                registros = self._extraer_texto_plano(soup, dni)
                
        except Exception as e:
            print(f"Error procesando {archivo_html}: {e}")
        
        return registros
    
    def _extraer_texto_plano(self, soup: BeautifulSoup, dni: str) -> List[RegistroProfesional]:
        """Extrae datos del texto plano si no hay tabla estructurada"""
        registros = []
        
        # Buscar en todo el texto
        texto = soup.get_text()
        
        # Patrones comunes
        # Buscar nombre: texto en mayúsculas con coma
        nombres_match = re.search(r'([A-ZÁÉÍÓÚÑ\s]+,\s*[A-ZÁÉÍÓÚÑ\s]+)', texto)
        nombres = nombres_match.group(1).strip() if nombres_match else ""
        
        # Buscar DNI
        dni_match = re.search(r'DNI\s*(\d{8})', texto)
        dni_encontrado = dni_match.group(1) if dni_match else dni
        
        # Buscar títulos comunes
        titulos = re.findall(r'(BACHILLER[A-ZÁÉÍÓÚÑ\s]+|LICENCIADO[A-ZÁÉÍÓÚÑ\s]+|INGENIERO[A-ZÁÉÍÓÚÑ\s]+|MÉDICO[A-ZÁÉÍÓÚÑ\s]+|ABOGADO[A-ZÁÉÍÓÚÑ\s]+)', texto)
        
        # Buscar universidades
        universidades = re.findall(r'(UNIVERSIDAD[A-ZÁÉÍÓÚÑ\s]+|INSTITUTO[A-ZÁÉÍÓÚÑ\s]+)', texto)
        
        if nombres or titulos:
            for i, titulo in enumerate(titulos[:2]):  # Máximo 2 títulos
                registro = RegistroProfesional(
                    dni=dni_encontrado,
                    nombres=nombres,
                    grado_o_titulo=titulo.strip(),
                    institucion=universidades[i] if i < len(universidades) else "",
                    fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    estado="ENCONTRADO"
                )
                registros.append(registro)
        
        return registros
    
    def procesar_carpeta(self):
        """Procesa todos los HTML en la carpeta"""
        archivos = list(self.input_dir.glob("*.html")) + list(self.input_dir.glob("*.htm"))
        
        if not archivos:
            print(f"\n[INFO] No hay archivos HTML en '{self.input_dir}'")
            print("[INSTRUCCIONES]:")
            print("  1. Abre tu navegador normal (Chrome, Edge, Firefox)")
            print("  2. Ve a: https://constanciasweb.sunedu.gob.pe/#/modulos/grados-y-titulos")
            print("  3. Ingresa un DNI y resuelve el CAPTCHA")
            print("  4. Cuando aparezcan los resultados, guarda la página:")
            print("     - Presiona Ctrl+S")
            print("     - Guarda como 'Pagina web completa'")
            print("     - Guarda en la carpeta 'html_consultas'")
            print("  5. Repite para cada DNI")
            print("  6. Ejecuta este script para extraer los datos")
            return
        
        print(f"\n[INFO] Procesando {len(archivos)} archivos HTML...")
        
        for archivo in archivos:
            print(f"\nProcesando: {archivo.name}")
            
            # Intentar extraer DNI del nombre del archivo
            dni_match = re.search(r'(\d{7,8})', archivo.name)
            dni = dni_match.group(1) if dni_match else ""
            
            registros = self.extraer_de_html(str(archivo), dni)
            self.resultados.extend(registros)
            
            print(f"  [OK] {len(registros)} registro(s) extraido(s)")
        
        # Guardar resultados
        self._guardar_resultados()
    
    def _guardar_resultados(self):
        """Guarda resultados en Excel y CSV"""
        if not self.resultados:
            print("[WARNING] No hay resultados para guardar")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        datos = [asdict(r) for r in self.resultados]
        df = pd.DataFrame(datos)
        
        # Excel
        excel_path = self.output_dir / f"SUNEDU_Extract_{timestamp}.xlsx"
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
        # CSV
        csv_path = self.output_dir / f"SUNEDU_Extract_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        print(f"\n[OK] Resultados guardados:")
        print(f"  Excel: {excel_path}")
        print(f"  CSV: {csv_path}")


def main():
    print("="*70)
    print("  SUNEDU EXTRACTOR - Extraccion de HTML guardado")
    print("="*70)
    print("\nEste script extrae datos de paginas HTML guardadas de SUNEDU.")
    print("No requiere automatizacion de navegador.")
    print("="*70)
    
    extractor = SuneduExtractor()
    extractor.procesar_carpeta()
    
    print("\n[OK] Proceso finalizado")


if __name__ == "__main__":
    main()

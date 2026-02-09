#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUNEDU CLIPBOARD BOT
Tú haces la consulta manualmente en cualquier navegador,
copias los resultados al portapapeles (Ctrl+C),
y este script los procesa y guarda en Excel.

VENTAJAS:
- Funciona con CUALQUIER navegador (Chrome, Edge, Firefox, Opera)
- Cero problemas con CAPTCHA
- Cero detección de bots
- Muy rápido
"""

import re
import time
import pandas as pd
import pyperclip
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional


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


class SuneduClipboardBot:
    """Procesa datos copiados de SUNEDU"""
    
    def __init__(self):
        self.resultados: List[RegistroProfesional] = []
        self.output_dir = Path("resultados")
        self.output_dir.mkdir(exist_ok=True)
    
    def _log(self, mensaje: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {mensaje}")
    
    def esperar_portapapeles(self, dni: str) -> str:
        """Espera a que el usuario copie datos al portapapeles"""
        print("\n" + "="*70)
        print(f"DNI: {dni}")
        print("="*70)
        print("""
[INSTRUCCIONES]:
  1. En tu navegador, selecciona los resultados de la consulta
  2. Presiona Ctrl+C para copiar
  3. Vuelve aquí y presiona ENTER

[TIP]: Selecciona toda la tabla con los datos:
       - Nombre completo
       - Grado/Título
       - Institución
       - Fechas
""")
        print("="*70)
        
        input("\n[ENTER] Presiona ENTER despues de copiar los datos...")
        
        try:
            # Obtener texto del portapapeles
            texto = pyperclip.paste()
            
            if not texto or len(texto) < 20:
                print("[!] No se detecto texto en el portapapeles")
                respuesta = input("[?] Intentar de nuevo? (s/n): ")
                if respuesta.lower() == 's':
                    return self.esperar_portapapeles(dni)
                return ""
            
            print(f"[OK] Texto capturado: {len(texto)} caracteres")
            return texto
            
        except Exception as e:
            print(f"[!] Error leyendo portapapeles: {e}")
            return ""
    
    def extraer_datos(self, texto: str, dni: str) -> List[RegistroProfesional]:
        """Extrae datos del texto copiado"""
        registros = []
        
        try:
            # Limpiar texto
            lineas = [l.strip() for l in texto.split('\n') if l.strip()]
            texto_completo = ' '.join(lineas)
            
            # Buscar nombre: formato "APELLIDO, NOMBRE"
            nombres = ""
            nombre_match = re.search(r'([A-ZÁÉÍÓÚÑ\s]+,\s*[A-ZÁÉÍÓÚÑ\s]+)', texto_completo)
            if nombre_match:
                nombres = nombre_match.group(1).strip()
            
            # Buscar DNI
            dni_match = re.search(r'DNI\s*(\d{7,8})', texto_completo)
            dni_encontrado = dni_match.group(1) if dni_match else dni
            
            # Buscar títulos académicos
            titulos = []
            
            # Patrones de títulos comunes
            patrones_titulo = [
                r'BACHILLER[A-ZÁÉÍÓÚÑ\s]+',
                r'LICENCIADO[A-ZÁÉÍÓÚÑ\s]+',
                r'INGENIERO[A-ZÁÉÍÓÚÑ\s]+',
                r'MÉDICO[A-ZÁÉÍÓÚÑ\s]+',
                r'ABOGADO[A-ZÁÉÍÓÚÑ\s]+',
                r'MAGISTER[A-ZÁÉÍÓÚÑ\s]+',
                r'DOCTOR[A-ZÁÉÍÓÚÑ\s]+',
            ]
            
            for patron in patrones_titulo:
                matches = re.findall(patron, texto_completo.upper())
                for match in matches:
                    titulo = match.strip()
                    if len(titulo) > 5 and titulo not in [t['titulo'] for t in titulos]:
                        # Buscar fechas asociadas
                        idx = texto_completo.upper().find(titulo)
                        contexto = texto_completo[max(0, idx-100):idx+200]
                        
                        fecha_diploma = ""
                        fecha_matricula = "Sin información"
                        fecha_egreso = "Sin información"
                        
                        # Buscar fechas en formato dd/mm/yyyy
                        fechas = re.findall(r'\d{2}/\d{2}/\d{4}', contexto)
                        if fechas:
                            fecha_diploma = fechas[0]
                        
                        # Buscar "Sin información"
                        if "sin información" in contexto.lower():
                            partes = contexto.lower().split("sin información")
                            # Contar cuántos "Sin información" hay
                            count = contexto.lower().count("sin información")
                            if count >= 1:
                                fecha_matricula = "Sin información"
                            if count >= 2:
                                fecha_egreso = "Sin información"
                        
                        titulos.append({
                            'titulo': titulo,
                            'diploma': fecha_diploma,
                            'matricula': fecha_matricula,
                            'egreso': fecha_egreso
                        })
            
            # Buscar institución
            institucion = ""
            institucion_match = re.search(r'(UNIVERSIDAD[A-ZÁÉÍÓÚÑ\s]+|INSTITUTO[A-ZÁÉÍÓÚÑ\s]+|ESCUELA[A-ZÁÉÍÓÚÑ\s]+)', texto_completo.upper())
            if institucion_match:
                institucion = institucion_match.group(1).strip()
            
            # Crear registros
            if titulos:
                for t in titulos:
                    registro = RegistroProfesional(
                        dni=dni_encontrado,
                        nombres=nombres,
                        grado_o_titulo=t['titulo'],
                        institucion=institucion,
                        fecha_diploma=t['diploma'],
                        fecha_matricula=t['matricula'],
                        fecha_egreso=t['egreso'],
                        fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        estado="ENCONTRADO"
                    )
                    registros.append(registro)
            elif nombres:
                # Al menos encontramos el nombre
                registro = RegistroProfesional(
                    dni=dni_encontrado,
                    nombres=nombres,
                    institucion=institucion,
                    fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    estado="ENCONTRADO"
                )
                registros.append(registro)
            else:
                # No se encontró nada útil
                registro = RegistroProfesional(
                    dni=dni_encontrado,
                    estado="NO ENCONTRADO",
                    observaciones=texto_completo[:200],
                    fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                registros.append(registro)
            
        except Exception as e:
            self._log(f"Error extrayendo datos: {e}")
            registros.append(RegistroProfesional(
                dni=dni,
                estado="ERROR",
                observaciones=str(e)[:200],
                fecha_consulta=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        
        return registros
    
    def procesar_dnis(self, archivo: str):
        """Procesa lista de DNIs"""
        dnis = self._leer_dnis(archivo)
        if not dnis:
            print("[!] No se encontraron DNIs")
            return
        
        print("\n" + "="*70)
        print("SUNEDU CLIPBOARD BOT")
        print(f"Total DNIs: {len(dnis)}")
        print("="*70)
        print("\nEste modo funciona con CUALQUIER navegador:")
        print("- Chrome, Edge, Firefox, Opera, Safari")
        print("- Sin problemas de CAPTCHA")
        print("- Sin deteccion de bots")
        print("="*70)
        
        for i, dni in enumerate(dnis, 1):
            # Esperar datos del portapapeles
            texto = self.esperar_portapapeles(dni)
            
            if not texto:
                continue
            
            # Extraer datos
            registros = self.extraer_datos(texto, dni)
            self.resultados.extend(registros)
            
            # Mostrar resumen
            print(f"\n[OK] Registros extraidos: {len(registros)}")
            for r in registros:
                print(f"    - {r.grado_o_titulo or r.nombres or 'Sin titulo'}")
            
            # Guardar progreso
            if i % 5 == 0 or i == len(dnis):
                self._guardar_resultados(f"_progreso_{i}")
            
            # Preguntar continuar
            if i < len(dnis):
                respuesta = input(f"\n[?] Continuar con el siguiente DNI? (s/n): ").strip().lower()
                if respuesta != 's':
                    break
        
        # Guardar final
        self._guardar_resultados("_final")
        self._mostrar_resumen()
    
    def _leer_dnis(self, archivo: str) -> List[str]:
        """Lee DNIs desde archivo"""
        dnis = []
        path = Path(archivo)
        
        if not path.exists():
            return []
        
        try:
            if archivo.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(archivo, dtype=str)
            else:
                df = pd.read_csv(archivo, dtype=str)
            
            for col in df.columns:
                if col.upper() in ['DNI', 'DOCUMENTO', 'NUMERO']:
                    dnis = df[col].dropna().astype(str).str.strip().tolist()
                    break
            
            dnis = [d for d in dnis if d.isdigit()]
            dnis = list(dict.fromkeys(dnis))
            
        except Exception as e:
            print(f"[!] Error leyendo archivo: {e}")
        
        return dnis
    
    def _guardar_resultados(self, sufijo: str = ""):
        """Guarda resultados"""
        if not self.resultados:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        datos = [asdict(r) for r in self.resultados]
        df = pd.DataFrame(datos)
        
        excel_path = self.output_dir / f"SUNEDU_CLIP{sufijo}_{timestamp}.xlsx"
        df.to_excel(excel_path, index=False, engine='openpyxl')
        
        csv_path = self.output_dir / f"SUNEDU_CLIP{sufijo}_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        self._log(f"Guardado: {excel_path.name}")
    
    def _mostrar_resumen(self):
        """Muestra resumen"""
        print("\n" + "="*70)
        print("RESUMEN")
        print("="*70)
        print(f"Total registros: {len(self.resultados)}")
        encontrados = sum(1 for r in self.resultados if r.estado == "ENCONTRADO")
        print(f"Encontrados: {encontrados}")
        print(f"No encontrados: {len(self.resultados) - encontrados}")
        print("="*70)


def main():
    import sys
    
    print("="*70)
    print("  SUNEDU CLIPBOARD BOT")
    print("="*70)
    print("\nFunciona con CUALQUIER navegador!")
    print("="*70)
    
    # Verificar pyperclip
    try:
        import pyperclip
    except ImportError:
        print("\n[!] Se requiere instalar 'pyperclip'")
        print("Ejecuta: pip install pyperclip")
        return
    
    archivo = sys.argv[1] if len(sys.argv) > 1 else "dni_lista.csv"
    
    bot = SuneduClipboardBot()
    bot.procesar_dnis(archivo)
    
    print("\n[OK] PROCESO FINALIZADO")


if __name__ == "__main__":
    main()

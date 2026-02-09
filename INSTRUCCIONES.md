# 🎓 SUNEDU BOT - Instrucciones de Uso

## 📋 Descripción

Sistema automatizado con **anti-detección** para consultar el Registro Nacional de Grados y Títulos de SUNEDU Perú. Usa `undetected-chromedriver` para evadir Cloudflare Turnstile.

## ⚡ Instalación Rápida

### Paso 1: Instalar dependencias

**Opción A - Automática (Recomendado):**
```
Doble clic en: instalar.bat
```

**Opción B - Manual:**
```bash
pip install selenium undetected-chromedriver webdriver-manager
pip install pandas openpyxl beautifulsoup4 fake-useragent
```

### Paso 2: Verificar instalación

```bash
python test_instalacion.py
```

Debe decir: `✅ TODO LISTO`

---

## 🚀 Uso

### Forma 1: Archivo por defecto (dni_lista.csv)
```bash
python sunedu_bot.py
```

### Forma 2: Tu propio archivo
```bash
python sunedu_bot.py mis_dnis.csv
```

### Forma 3: Ejecutable batch
```
Doble clic en: ejecutar.bat
```

---

## ⚙️ Configuración

Edita `config.json`:

```json
{
  "delay_min": 8,          // Segundos mínimos entre consultas
  "delay_max": 15,         // Segundos máximos entre consultas
  "timeout_captcha": 180,  // Tiempo esperando CAPTCHA (segundos)
  "guardar_cada": 5,       // Guardar progreso cada N registros
  "reintentos": 2,         // Reintentos si falla
  "headless": false        // false = ves el navegador
}
```

---

## 🔄 Proceso de Uso

```
1. Script abre Chrome automáticamente
2. Navega a SUNEDU
3. Ingresa el primer DNI
4. Si aparece CAPTCHA → Se pausa
5. Tú resuelves el CAPTCHA manualmente
6. Presionas ENTER en la consola
7. Script extrae datos automáticamente
8. Guarda en Excel/CSV/TXT
9. Espera 8-15 segundos (aleatorio)
10. Repite con siguiente DNI
```

---

## 📁 Archivos de Salida

Se crean en la carpeta `resultados/`:

| Archivo | Descripción |
|---------|-------------|
| `SUNEDU_Resultados_final_*.xlsx` | Excel con todos los datos |
| `SUNEDU_Resultados_final_*.csv` | CSV para importar en cualquier sistema |
| `SUNEDU_Resultados_final_*.txt` | Formato legible para humanos |

También se guardan progresos parciales cada 5 DNIs.

---

## 📊 Formato de Salida (TXT)

```
════════════════════════════════════════════════════════════════════════════════
SUNEDU - REGISTRO NACIONAL DE GRADOS Y TÍTULOS
Generado: 2024-02-05 14:30:25
════════════════════════════════════════════════════════════════════════════════

────────────────────────────────────────────────────────────────────────────────
DNI: 10173113
Nombres: CABANA EGOAVIL, ROSARIO SOLEDAD
Grado/Título: BACHILLER EN CIENCIAS DE LA SALUD ENFERMERIA
Institución: UNIVERSIDAD PERUANA UNIÓN
Fecha Diploma: 14/04/1997
Fecha Matrícula: Sin información
Fecha Egreso: Sin información
País: PERU
Estado: ENCONTRADO
Consulta: 2024-02-05 14:30:45
```

---

## 📋 Tu Lista de DNIs

Ya está cargada en `dni_lista.csv` con **140 DNIs** listos para procesar.

Si quieres usar otro archivo, créalo con este formato:

**CSV:**
```csv
DNI
10173113
12345678
87654321
```

**Excel:**
Columna llamada `DNI` con los números.

---

## 🔧 Solución de Problemas

### Error "undetected_chromedriver no encontrado"
```bash
pip install undetected-chromedriver --upgrade
```

### Chrome no se abre
- Cierra todas las ventanas de Chrome
- Verifica que Chrome esté instalado
- Prueba cambiar `"headless": false` a `true`

### CAPTCHA aparece constantemente
- Es normal, SUNEDU tiene protección
- Resuélvelo manualmente cuando aparezca
- Los delays aleatorios ayudan a reducir frecuencia

### Error "session not created"
- Chrome puede estar actualizándose
- Espera unos minutos e intenta de nuevo
- O ejecuta: `pip install undetected-chromedriver --upgrade`

---

## ⚠️ Notas Importantes

1. **CAPTCHA Manual**: El script NO resuelve CAPTCHAs automáticamente (eso requeriría servicios pagos). Debes resolverlos manualmente.

2. **Paciencia**: Con 140 DNIs, el proceso puede tomar varias horas debido a los delays de seguridad.

3. **No cierres el navegador**: Deja que el script controle Chrome.

4. **Progreso guardado**: Cada 5 DNIs se guarda automáticamente, así que si se interrumpe no pierdes todo.

5. **Logs**: Revisa la carpeta `logs/` para ver el historial detallado.

---

## 📞 Resumen de Comandos

```bash
# Instalar
instalar.bat

# Verificar
python test_instalacion.py

# Ejecutar
python sunedu_bot.py

# Con archivo personalizado
python sunedu_bot.py tu_archivo.csv
```

---

**¡Listo! Con esto puedes procesar tus 140 DNIs automáticamente.** 🚀

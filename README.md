# 🎓 SUNEDU Scraper - Automatización de Consultas

Sistema automatizado para consultar el **Registro Nacional de Grados Académicos y Títulos Profesionales** de SUNEDU Perú.

## 📋 Características

- ✅ Consulta automática por DNI
- ✅ Extracción de: Nombres, Grado/Título, Institución, Fechas
- ✅ Procesamiento masivo (100+ DNIs)
- ✅ Exportación a Excel y CSV
- ✅ Manejo de CAPTCHA (resolución manual)
- ✅ Screenshots para diagnóstico
- ✅ Guardado de progreso parcial

## 🚀 Instalación Rápida

### Opción 1: Ejecutar instalador (Windows)
```bash
# Doble clic en:
instalar.bat

# O en PowerShell:
.\instalar.ps1
```

### Opción 2: Instalación manual
```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Instalar navegador Chromium para Playwright
playwright install chromium
```

## 📖 Uso

### 1. Preparar lista de DNIs

Edita el archivo `dni_lista.csv`:
```csv
DNI
10173113
12345678
87654321
```

O usa un archivo Excel `dni_lista.xlsx` con una columna llamada "DNI".

### 2. Ejecutar el scraper

```bash
# Forma simple
python sunedu_scraper.py

# Con archivo personalizado
python sunedu_scraper.py mi_lista.csv

# O usa el ejecutable batch
ejecutar.bat
```

### 3. Resolver CAPTCHA (manual)

Cuando aparezca el CAPTCHA:
1. **Completa el CAPTCHA** en la ventana del navegador
2. **Presiona ENTER** en la consola/terminal
3. El scraper continuará automáticamente

### 4. Resultados

Los resultados se guardan en la carpeta `resultados/`:
- `resultados_sunedu_YYYYMMDD_HHMMSS.xlsx`
- `resultados_sunedu_YYYYMMDD_HHMMSS.csv`

## ⚙️ Configuración

Edita `config.json` para personalizar:

```json
{
  "timeout_captcha": 120,      // Segundos esperando CAPTCHA
  "delay_entre_consultas": 3,   // Segundos entre cada DNI
  "headless": false,            // false = ver navegador
  "guardar_screenshots": true,  // Guardar capturas de pantalla
  "exportar_formato": "excel"   // Formato de salida
}
```

## 📊 Estructura de Resultados

| Columna | Descripción |
|---------|-------------|
| dni | Número de DNI consultado |
| nombres | Nombre completo del graduado |
| grado_o_titulo | Grado o título obtenido |
| institucion | Universidad/Institución |
| fecha_diploma | Fecha de expedición del diploma |
| fecha_matricula | Fecha de matrícula (si aplica) |
| fecha_egreso | Fecha de egreso (si aplica) |
| pais | País |
| estado | ENCONTRADO / NO ENCONTRADO |
| fecha_consulta | Fecha y hora de la consulta |

## 🛠️ Solución de Problemas

### Error: "playwright not found"
```bash
pip install playwright
playwright install chromium
```

### Error: "chromedriver not found" (Selenium)
```bash
pip install webdriver-manager
```

### El navegador no abre
- Cambia `"headless": false` a `true` en `config.json`
- Verifica que no haya otro Chrome abierto

### No encuentra el campo de DNI
- La página puede haber cambiado
- Revisa los screenshots en la carpeta `screenshots/`
- Actualiza los selectores en el código si es necesario

## 🔍 Ejemplo de Salida

```
========================================
     SUNEDU SCRAPER
========================================

📁 Archivo de entrada: dni_lista.csv

📋 TOTAL DE DNIs A PROCESAR: 100

────────────────────────────────────────
📌 Procesando 1/100: DNI 10173113
────────────────────────────────────────
🌐 Navegando a SUNEDU...
   ✏️  DNI ingresado: 10173113
   🔒 CAPTCHA detectado!

========================================
DNI A CONSULTAR: 10173113
========================================

⚠️  ACCIÓN REQUERIDA:
   1. Completa el CAPTCHA en la página
   2. Presiona ENTER cuando termines...

👉 Presiona ENTER cuando hayas completado el CAPTCHA... 

   ⏳ Esperando resultados...
   📊 Se encontraron 2 registro(s)
   ✅ Registro 1: BACHILLER EN CIENCIAS DE LA SALUD ENFERMERIA
   ✅ Registro 2: LICENCIADO EN ENFERMERIA
   ⏱️  Esperando 3 segundos...

💾 Resultados guardados:
   📊 Excel: resultados\resultados_sunedu_20240205_134037.xlsx
   📄 CSV: resultados\resultados_sunedu_20240205_134037.csv
```

## 📝 Notas Importantes

1. **CAPTCHA**: SUNEDU usa protección anti-bot. El script pausa para resolución manual.

2. **Tiempos**: Respeta los delays entre consultas para no saturar el servidor.

3. **Legales**: Usa este script solo para fines legítimos y con autorización.

4. **Actualizaciones**: Si SUNEDU cambia su web, los selectores CSS pueden necesitar actualización.

## 🔄 Alternativas

Si Playwright no funciona, prueba la versión Selenium:
```bash
python sunedu_selenium.py dni_lista.csv
```

## 📞 Soporte

Para problemas técnicos:
1. Revisa los screenshots en `screenshots/`
2. Verifica que tu lista de DNIs esté bien formateada
3. Asegúrate de tener conexión a internet estable

---
**Desarrollado para automatización de consultas SUNEDU**
⚠️ Úsalo responsablemente

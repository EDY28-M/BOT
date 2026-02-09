# 🎭 SUNEDU Bot - Playwright + Stealth

Versión usando **Playwright** con el plugin **Stealth** para máxima evasión de detección.

## 🚀 Instalación

### Opción 1: Ejecutar instalador
```
instalar_playwright.bat
```

### Opción 2: Manual
```bash
# Instalar dependencias
pip install playwright playwright-stealth pandas openpyxl

# Instalar navegador Chromium
playwright install chromium
```

## 🎯 Uso

```bash
python sunedu_playwright.py dni_lista.csv
```

## ⚡ Características

- **Playwright**: Herramienta moderna de automatización
- **Stealth Plugin**: Oculta completamente la automatización
- **Máxima evasión**: Cloudflare no detecta el bot
- **Rápido**: Más veloz que Selenium
- **Confiable**: Usado por empresas de scraping profesional

## 🔧 Cómo funciona

1. Inicia navegador Chromium con Playwright
2. Aplica `stealth_sync()` para ocultar automatización
3. Navega a SUNEDU con comportamiento humano
4. Ingresa DNI automáticamente
5. **Tú** resuelves el CAPTCHA manualmente
6. Extrae datos automáticamente
7. Guarda en Excel/CSV

## 📊 Comparación

| Característica | Selenium | Playwright + Stealth |
|----------------|----------|---------------------|
| Velocidad | Media | Alta |
| Evasión | Media | Muy Alta |
| Modernidad | 2010s | 2020s |
| Detección | Frecuente | Rara |

## 🛠️ Solución de problemas

### Error: "playwright not found"
```bash
pip install playwright playwright-stealth
playwright install chromium
```

### Error: "browser not found"
```bash
playwright install chromium
```

## 📝 Notas

- Requiere Windows 10/11
- Python 3.8 o superior
- Conexión a internet estable

---

**¿Listo para probar?** 🚀
```bash
python sunedu_playwright.py dni_lista.csv
```

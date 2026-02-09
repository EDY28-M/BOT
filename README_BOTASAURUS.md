# 🦖 SUNEDU Bot - Botasaurus Edition

## ¿Qué es Botasaurus?

**Botasaurus** es un framework de web scraping especializado en **evadir la detección de bots**. Es conocido por ser muy efectivo contra Cloudflare, DataDome y otros sistemas de protección.

🔗 https://github.com/omkarcloud/botasaurus

## 🚀 Instalación

### Opción 1: Automática
```
instalar_botasaurus.bat
```

### Opción 2: Manual
```bash
pip install botasaurus pandas openpyxl
```

## 🎯 Uso

```bash
python sunedu_botasaurus.py dni_lista.csv
```

## ⚡ Características de Botasaurus

- **Anti-detection built-in**: Evasión nativa de bots
- **Fingerprint spoofing**: Falsifica fingerprints del navegador
- **Human-like behavior**: Comportamiento humano automático
- **Block resources**: Bloquea imágenes y recursos para velocidad
- **Moderno**: Framework 2023-2024

## 🔧 ¿Por qué Botasaurus?

| Característica | Selenium | Playwright | Botasaurus |
|----------------|----------|------------|------------|
| Anti-detection | ❌ Manual | ❌ Manual | ✅ Built-in |
| Facilidad | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Efectividad | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Mantenimiento | Activo | Activo | Muy Activo |

## 🛠️ Solución de problemas

### Error: "botasaurus not found"
```bash
pip install botasaurus
```

### Error: "chromedriver not found"
Botasaurus maneja los drivers automáticamente, no necesitas instalarlos.

## 📝 Nota importante

Aunque Botasaurus es muy efectivo, **Cloudflare Turnstile** sigue siendo muy agresivo. Si detecta el bot:

1. El script se pausará
2. **Tú** resuelves el CAPTCHA manualmente
3. Presionas ENTER para continuar
4. El bot extrae los datos

## 🏆 Comparación con otras opciones

```
1. Botasaurus    - Máxima evasión (intentar primero)
2. Playwright    - Moderno pero detectable
3. Selenium      - Básico, fácilmente detectado
4. Portapapeles  - 100% manual, 100% efectivo
```

---

**¿Listo para probar?** 🦖🚀

```bash
python sunedu_botasaurus.py dni_lista.csv
```

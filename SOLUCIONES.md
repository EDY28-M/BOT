# 🛠️ SOLUCIONES para el Error de Cloudflare

Cloudflare está detectando la automatización. Aquí tienes **3 opciones** para resolverlo:

---

## 🔵 OPCIÓN 1: Modo Manual Asistido (RECOMENDADA)

**Archivo:** `sunedu_bot_v2.py`

El bot abre Chrome, pero **TÚ** ingresas el DNI y resuelves el CAPTCHA manualmente. Luego el bot extrae los datos automáticamente.

### Ventajas:
- ✅ No hay detección de bots (tú controlas el navegador)
- ✅ CAPTCHA siempre funciona
- ✅ Extracción automática de datos
- ✅ Guardado en Excel/CSV automático

### Instrucciones:
```bash
python sunedu_bot_v2.py
```

1. Se abrirá Chrome automáticamente
2. Ingresa el **DNI** manualmente en el campo
3. Resuelve el **CAPTCHA** (marca "No soy un robot")
4. Haz clic en **"Buscar"**
5. Espera que carguen los resultados
6. Vuelve a la consola y presiona **ENTER**
7. El bot extraerá los datos automáticamente
8. Se guardarán en `resultados/`

---

## 🟢 OPCIÓN 2: Extracción desde HTML Guardado (100% Segura)

**Archivo:** `sunedu_extractor.py`

Haces las consultas **manualmente en tu navegador normal**, guardas cada página como HTML, y el bot extrae los datos de los archivos.

### Ventajas:
- ✅ 100% indetectable (usas tu navegador normal)
- ✅ Cero problemas con CAPTCHA
- ✅ Puedes hacer las consultas a tu ritmo
- ✅ Extrae datos de múltiples archivos de una vez

### Instrucciones:

**Paso 1:** Abre tu navegador normal (Chrome, Edge, Firefox)

**Paso 2:** Ve a:
```
https://constanciasweb.sunedu.gob.pe/#/modulos/grados-y-titulos
```

**Paso 3:** Ingresa un DNI y resuelve el CAPTCHA

**Paso 4:** Cuando aparezcan los resultados, **guarda la página**:
- Presiona `Ctrl+S`
- Selecciona "Página web completa" o "HTML"
- Guarda en la carpeta `html_consultas/`
- Usa nombre descriptivo: `10173113.html`

**Paso 5:** Repite para cada DNI

**Paso 6:** Ejecuta el extractor:
```bash
python sunedu_extractor.py
```

El script procesará todos los HTML y creará el Excel/CSV.

---

## 🟡 OPCIÓN 3: Modo Automático Original (Menos Confiable)

**Archivo:** `sunedu_bot.py`

Intenta hacer todo automáticamente, pero Cloudflare puede detectarlo.

### Instrucciones:
```bash
python sunedu_bot.py
```

**Si da error de CAPTCHA:** Usa la Opción 1 o 2

---

## 📊 Comparación Rápida

| Característica | Opción 1 (Manual) | Opción 2 (HTML) | Opción 3 (Auto) |
|----------------|-------------------|-----------------|-----------------|
| **Detección** | ❌ Ninguna | ❌ Ninguna | ⚠️ Posible |
| **Velocidad** | ⚡ Media | 🐌 Lenta | ⚡ Rápida |
| **Confiabilidad** | ✅ Alta | ✅ Muy Alta | ⚠️ Media |
| **Esuerzo** | 📝 Medio | 📝 Alto | 🤖 Bajo |
| **Cantidad** | Buena para 100+ | Mejor para <50 | Buena si funciona |

---

## 🎯 Mi Recomendación

Para tus **131 DNIs**:

### Si tienes tiempo y quieres 100% confiable:
**Usa OPCIÓN 2 (HTML)**
- Tarda más pero siempre funciona
- Puedes hacerlo en varias sesiones
- No hay riesgo de bloqueo

### Si quieres velocidad moderada:
**Usa OPCIÓN 1 (Manual Asistido)**
- El bot ayuda con la extracción
- Tú solo ingresas DNI y CAPTCHA
- Más rápido que guardar HTMLs

### Si quieres probar primero:
```bash
# Prueba con un solo DNI
python sunedu_bot_v2.py

# Si funciona bien, continua con todos
# Si no, usa sunedu_extractor.py
```

---

## 🚀 Comandos Rápidos

```bash
# OPCIÓN 1: Manual Asistido (Recomendada)
python sunedu_bot_v2.py

# OPCIÓN 2: Extracción HTML
python sunedu_extractor.py

# OPCIÓN 3: Automático (puede fallar)
python sunedu_bot.py
```

---

## 💡 Tips para OPCIÓN 2 (HTML)

1. **Organiza por lotes:** Divide los 131 DNIs en grupos de 20-30
2. **Nombra bien los archivos:** `001-10173113.html`, `002-8801713.html`
3. **Verifica cada resultado:** Antes de guardar, confirma que cargó bien
4. **Backup:** Guarda los HTMLs como respaldo

---

## ⚠️ Importante

- SUNEDU tiene protección anti-bot legítima
- No intentes automatizar el CAPTCHA (es ilegal en muchos países)
- Respeta los términos de servicio
- Usa estas herramientas solo para fines legítimos

---

**¿Cuál opción prefieres usar?** 🤔

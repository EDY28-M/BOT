# 🎯 TODAS LAS OPCIONES DISPONIBLES

Cloudflare está detectando Chrome. Aquí tienes **6 alternativas**:

---

## 🟢 OPCIÓN 1: Microsoft Edge (CORREGIDA)

**Archivo:** `sunedu_edge.py`

```bash
python sunedu_edge.py
```

Usa Edge con perfil temporal limpio (sin conflictos de sesión).

---

## 🟢 OPCIÓN 2: Mozilla Firefox (NUEVA)

**Archivo:** `sunedu_firefox.py`

```bash
python sunedu_firefox.py
```

Usa Firefox. A veces Firefox tiene menos problemas con Selenium.

**Requisito:** Tener Firefox instalado (descarga desde https://firefox.com)

---

## 🟢 OPCIÓN 3: Portapapeles (CLIPBOARD) - MÁS CONFIABLE

**Archivo:** `sunedu_clipboard.py`

```bash
# Instalar dependencia:
pip install pyperclip

# Ejecutar:
python sunedu_clipboard.py
```

Funciona con **CUALQUIER navegador** manualmente.

**Flujo:**
1. Abre tu navegador favorito (Chrome, Edge, Firefox, Opera)
2. Ve a SUNEDU e ingresa DNI + CAPTCHA manualmente
3. **Selecciona y copia** los resultados (Ctrl+C)
4. El bot lee el portapapeles y extrae datos
5. El bot guarda en Excel/CSV/TXT

---

## 🟡 OPCIÓN 4: Chrome Manual

**Archivo:** `sunedu_bot_v2.py`

```bash
python sunedu_bot_v2.py
```

---

## 🟡 OPCIÓN 5: Extracción HTML

**Archivo:** `sunedu_extractor.py`

```bash
python sunedu_extractor.py
```

Guarda páginas HTML manualmente y el bot extrae datos.

---

## 🔴 OPCIÓN 6: Automático (NO FUNCIONA)

**Archivo:** `sunedu_bot.py`

Cloudflare lo bloquea.

---

## 🏆 RECOMENDACIÓN FINAL

Dado que Chrome y Edge tienen problemas, prueba en este orden:

### 1️⃣ Firefox (Recomendada)
```bash
python sunedu_firefox.py
```

### 2️⃣ Si Firefox falla, usa Portapapeles (100% confiable)
```bash
pip install pyperclip
python sunedu_clipboard.py
```

La opción **Portapapeles** siempre funciona porque:
- Tú controlas el navegador completamente
- Solo copias y pegas texto
- Cero automatización del navegador
- Cero detección

---

## 📊 Comparación

| Opción | Navegador | Confiabilidad | Esfuerzo |
|--------|-----------|---------------|----------|
| 1. Edge | Edge | Media | Medio |
| 2. Firefox | Firefox | Alta | Medio |
| 3. Clipboard | Cualquiera | 100% | Medio |
| 4. Chrome | Chrome | Baja | Medio |
| 5. HTML | Cualquiera | 100% | Alto |

---

## 🚀 Comandos para probar AHORA

```bash
# Opción 1: Firefox (Prueba primero)
python sunedu_firefox.py

# Opción 2: Edge
python sunedu_edge.py

# Opción 3: Portapapeles (Si las otras fallan)
pip install pyperclip
python sunedu_clipboard.py
```

---

## 💡 Instrucciones para Portapapeles (Clipboard)

Si las opciones de navegador automático fallan:

1. **Abre tu navegador favorito** manualmente
2. **Ve a:** https://constanciasweb.sunedu.gob.pe/#/modulos/grados-y-titulos
3. **Ingresa un DNI** y resuelve el CAPTCHA
4. **Selecciona los resultados** con el mouse
5. **Presiona Ctrl+C** para copiar
6. **Vuelve a la terminal** y presiona ENTER
7. El bot extraerá los datos automáticamente
8. Repite para cada DNI

---

**¿Cuál opción quieres probar?** 🚀

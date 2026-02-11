# 🤖 BACKEND_REFACTORED — DNI Automation System

## 📋 Resumen

Backend refactorizado en **Python (FastAPI + Botasaurus)** para automatización de consultas DNI en **SUNEDU** y **MINEDU**. Incluye monitoreo profesional del navegador en tiempo real.

---

## 🏗️ Arquitectura

```
BACKEND_REFACTORED/
├── main.py                      # Entry point (Uvicorn + CORS)
├── app/
│   ├── core/
│   │   ├── config.py            # URLs, estados, tiempos, constantes
│   │   └── logging.py           # Configuración de logging
│   ├── db/
│   │   ├── session.py           # SQLAlchemy engine + sessions
│   │   ├── models.py            # Modelos: Registro, Lote
│   │   └── repository.py        # CRUD: tomar_siguiente, actualizar_resultado
│   ├── scrapers/
│   │   ├── sunedu.py            # 🔍 Scraper SUNEDU (Botasaurus + Monitoring)
│   │   ├── minedu.py            # 🔍 Scraper MINEDU (Botasaurus + OCR + Monitoring)
│   │   └── node_engine/         # (Motor Node.js experimental, no activo)
│   ├── services/
│   │   ├── excel_service.py     # Parseo de Excel/CSV
│   │   └── retry_service.py     # Lógica de reintentos
│   ├── workers/
│   │   ├── loops.py             # Worker loops (@browser decorators)
│   │   └── orchestrator.py      # Gestor de threads (start/stop/pause)
│   └── api/
│       └── endpoints.py         # FastAPI routes (/api/...)
└── data/
    └── registros.db             # SQLite database
```

---

## 🔌 Conexiones y Puertos

| Componente | URL | Puerto |
|---|---|---|
| **Backend (FastAPI)** | `http://127.0.0.1:8000` | `8000` |
| **Frontend (Vite/React)** | `http://localhost:3000` | `3000` |
| **SUNEDU** | `https://constanciasweb.sunedu.gob.pe` | HTTPS |
| **MINEDU** | `https://titulosinstitutos.minedu.gob.pe` | HTTPS |

### CORS
El backend acepta requests desde `http://localhost:3000` (frontend).

### Frontend Proxy
El frontend (`vite.config.js`) proxea `/api` → `http://127.0.0.1:8000/api`.

---

## 🚀 Cómo Ejecutar

### 1. Backend
```bash
cd APP/webapp/BACKEND_REFACTORED
pip install -r requirements.txt
python main.py
```

### 2. Frontend
```bash
cd APP/webapp/FRONTENDWORKER
npm install
npm run dev
```

### 3. Abrir
Navegar a `http://localhost:3000`

---

## 📡 API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/upload` | Subir Excel/CSV con DNIs |
| `GET` | `/api/status` | Estado general (conteos por fase) |
| `GET` | `/api/registros` | Lista de registros con paginación |
| `POST` | `/api/workers/start` | Iniciar workers Sunedu + Minedu |
| `POST` | `/api/workers/stop` | Detener workers completamente |
| `GET` | `/api/workers/status` | Estado de los workers |
| `POST` | `/api/retry` | Reintentar registros fallidos |
| `GET` | `/api/exportar` | Descargar resultados en Excel |
| `POST` | `/api/limpiar` | Borrar todos los datos |

---

## 🔄 Pipeline de Estados

```
PENDIENTE → PROCESANDO_SUNEDU → FOUND_SUNEDU ✅
                               → CHECK_MINEDU → PROCESANDO_MINEDU → FOUND_MINEDU ✅
                                                                   → NOT_FOUND ❌
                               → ERROR_SUNEDU ⚠️
                                              → ERROR_MINEDU ⚠️
```

---

## 🔍 Scrapers

### SUNEDU (`sunedu.py`)
- **Motor**: Botasaurus (Selenium wrapper con anti-detección)
- **Flujo**:
  1. Navega a la web de SUNEDU
  2. Detecta estado (Turnstile/checkbox/tabla/swal)
  3. Pasa verificación si aparece
  4. Ingresa DNI vía JavaScript (Angular reactive forms)
  5. Click en "Buscar"
  6. Espera resultado (tabla o modal)
  7. Extrae datos de la tabla
- **Tiempos**:
  - Carga inicial: **6s**
  - Pre-DNI: **2s**
  - Post-Turnstile fail: **7s**
  - Post-resultado: **2s**
- **Reintentos**: 5 intentos

### MINEDU (`minedu.py`)
- **Motor**: Botasaurus + ddddocr (OCR para captcha)
- **Flujo**:
  1. Navega a la web de MINEDU
  2. Ingresa DNI
  3. Captura imagen captcha → OCR con ddddocr
  4. Ingresa texto captcha
  5. Click en "Consultar"
  6. Detecta error de captcha → refresca y reintenta
  7. Extrae datos del resultado
- **Tiempos** (portados de `minedu_bot.py`):
  - Carga página: **2s**
  - Post-click búsqueda: **3s**
  - Check resultado: **5 intentos × 1s**
- **Reintentos**: 8 intentos

---

## 🛡️ Monitoreo Profesional del Navegador (CDP)

### ¿Qué es?
Un sistema de **instrumentación** del navegador que intercepta TODO lo que ocurre dentro de la web de SUNEDU/MINEDU, sin necesidad de tener su código fuente.

### ¿Cómo funciona? (Método Profesional)

```
Botasaurus abre Chrome
  ↓
CDP: Page.addScriptToEvaluateOnNewDocument(spyScript)
  ↓  ← El spy se inyecta ANTES del JS de la web
Chrome descarga HTML + JS + CSS de SUNEDU/MINEDU
  ↓
El spy ya está corriendo cuando el JS de la web se ejecuta
  ↓
Intercepta: console.*, fetch, XHR, errors, promises
  ↓
Los eventos se guardan en window.__capturedEvents
  ↓
Python los recoge con _collect_events() → los loguea en tu terminal
```

**Equivalencia con Playwright:**

| Playwright | Nuestro código (Botasaurus) |
|---|---|
| `page.addInitScript(spy)` | `selenium.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', spy)` |
| `page.exposeFunction('__pwLog', fn)` | `window.__capturedEvents[]` + `_collect_events()` |
| `page.on('console', ...)` | Override de `console.log/warn/error` en el spy |
| `page.on('pageerror', ...)` | `window.onerror` + `unhandledrejection` en el spy |
| `page.on('requestfailed', ...)` | Override de `fetch` + `XMLHttpRequest` en el spy |

### ¿Qué eventos captura?

| Evento | Interceptor | Ejemplo en consola |
|---|---|---|
| `console.log/warn/error` | Override `console.*` | `[BROWSER][CONSOLE.ERROR] Failed to load resource` |
| JS Errors | `window.onerror` | `[BROWSER][JS_ERROR] Cannot read prop @ app.js:142` |
| Promise Rejections | `unhandledrejection` | `[BROWSER][PROMISE_FAIL] Network timeout` |
| HTTP 4xx/5xx | Override `fetch` + `XHR.load` | `[BROWSER][HTTP_500] POST /api/consulta` |
| Network Failures | Override `fetch.catch` + `XHR.error` | `[BROWSER][NET_FAIL] GET /api - ERR_CONNECTION` |

### ¿Dónde se ven?
En tu **terminal Python** con prefijo `[BROWSER]`.

### ¿En qué archivos está?
- `app/scrapers/sunedu.py` → `MONITOR_INIT_SCRIPT` + `_setup_cdp_monitoring()` + `_collect_events()`
- `app/scrapers/minedu.py` → Misma implementación

### Fallback
Si CDP no está disponible (versión de Chrome incompatible), automáticamente usa inyección post-carga como fallback.


---

## 🔧 Cambios Implementados (Historial)

### 1. Refactorización Completa
- **Antes**: Todo en un solo archivo `workers.py` (855 líneas)
- **Después**: Separado en módulos (`scrapers/`, `workers/`, `api/`, `db/`, `core/`)

### 2. Tiempos de Espera SUNEDU
| Acción | Antes | Después |
|--------|-------|---------|
| Carga inicial | 3s | **6s** |
| Pre-DNI | 0s | **2s** |
| Turnstile fail | 2s | **7s** |
| Post-resultado | 0s | **2s** |
| Post-no-encontrado | 0s | **0.8s** |

### 3. Sincronización MINEDU con Bot Original
Toda la lógica de `MCP/BOT_MINEDU/minedu_bot.py` fue portada:
- Click directo (`btn.click()`) en vez de MouseEvent
- Espera post-click: **3s** (antes 0.5s)
- 5 intentos de verificación de resultado (antes 4)
- Tiempos de captcha y refresh ajustados

### 4. Control de Workers
- **Stop**: Ahora termina threads completamente (`stop_workers()`) en vez de pausar
- Esto evita conexiones zombie y errores al reiniciar

### 5. Logging Mejorado
- Excepciones usan `repr(e)` para capturar detalles completos
- Monitoreo profesional del navegador (ver sección anterior)

### 6. Motor Node.js (Experimental)
- Carpeta `app/scrapers/node_engine/` con Playwright
- **No activo** — Playwright no pasa el Turnstile de Sunedu
- Disponible como referencia para futuras implementaciones

---

## 📦 Dependencias

### Python
```
fastapi
uvicorn[standard]
sqlalchemy
pandas
openpyxl
python-multipart
botasaurus
ddddocr
```

### Node.js (Solo experimental)
```
playwright (en node_engine/)
```

---

## ⚙️ Configuración (`app/core/config.py`)

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `SUNEDU_URL` | `https://constanciasweb.sunedu.gob.pe/...` | URL de consulta |
| `MINEDU_URL` | `https://titulosinstitutos.minedu.gob.pe/` | URL de consulta |
| `SUNEDU_MAX_RETRIES` | `5` | Reintentos por DNI |
| `MINEDU_MAX_RETRIES` | `8` | Reintentos por DNI |
| `HEADLESS` | `False` | Mostrar navegador |
| `API_HOST` | `127.0.0.1` | Host del servidor |
| `API_PORT` | `8000` | Puerto del servidor |
| `WORKER_POLL_INTERVAL` | `2` | Segundos entre polling |

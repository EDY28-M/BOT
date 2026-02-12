# SISTEMA DE CONSULTAS GRADOS Y TITULOS (SCGT) — DNI Automation System

## Requisitos del Equipo

> ⚠️ **IMPORTANTE**: Este sistema ejecuta dos navegadores Chrome en simultáneo (SUNEDU + MINEDU) con scraping en tiempo real. Se requiere hardware adecuado para evitar cuellos de botella.

| Componente | Mínimo Requerido | Recomendado |
|------------|-----------------|-------------|
| **Procesador** | Intel Core i5 10ª Gen / AMD Ryzen 5 3600 | Intel Core i7 11ª Gen+ / AMD Ryzen 7 5700+ |
| **RAM** | **16 GB** | 32 GB |
| **Almacenamiento** | **SSD (indispensable)** — NVME preferido | SSD NVME 256GB+ |
| **Sistema Operativo** | Windows 10 (64-bit) | Windows 11 |
| **Google Chrome** | v110+ (instalado) | Última versión estable |
| **Python** | 3.10+ | 3.11+ |
| **Node.js** | 18+ (solo para frontend) | 20 LTS |
| **Conexión Internet** | 10 Mbps estable | 50 Mbps+ |
| **Resolución Pantalla** | 1366×768 mínimo | 1920×1080 |
| **Acceso a internet** | Si | Si |

> ❌ **NO usar con HDD mecánico** — Los tiempos de carga del navegador serán excesivos y causarán timeouts en scraping.
>
> ❌ **NO usar con menos de 16 GB RAM** — Dos instancias de Chrome + Python + OCR requieren ~8-10 GB en uso activo.

---

## Resumen

Backend refactorizado en **Python (FastAPI + Botasaurus)** para automatización de consultas DNI en **SUNEDU** y **MINEDU**. Incluye:

- Web scraping con anti-detección (Botasaurus/Selenium)
- OCR de captcha MINEDU (ddddocr)
- Exportación Excel con 3 hojas, colores y formato profesional
- Recuperación automática de DNIs atascados
- Validación estricta de DNIs (8 dígitos)
- Monitoreo CDP del navegador en tiempo real
- Sistema de reintentos configurable

---

## Arquitectura

```
webapp/
├── BACKEND_REFACTORED/
│   ├── main.py                      # Entry point (Uvicorn + CORS + Auto-recovery)
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py            # URLs, estados, tiempos, constantes
│   │   │   └── logging.py           # Configuración de logging
│   │   ├── db/
│   │   │   ├── session.py           # SQLAlchemy engine + sessions
│   │   │   ├── models.py            # Modelos: Registro, Lote
│   │   │   └── repository.py        # CRUD: tomar_siguiente, actualizar_resultado, recuperar_procesando
│   │   ├── scrapers/
│   │   │   ├── sunedu.py            # Scraper SUNEDU (Botasaurus + Monitoring)
│   │   │   ├── minedu.py            # Scraper MINEDU (Botasaurus + OCR + Monitoring)
│   │   │   └── node_engine/         # (Motor Node.js experimental, no activo)
│   │   ├── services/
│   │   │   ├── excel_service.py     # Parseo + Exportación Excel (3 hojas, colores, Aptos Narrow)
│   │   │   └── retry_service.py     # Lógica de reintentos
│   │   ├── workers/
│   │   │   ├── loops.py             # Worker loops (sunedu_worker_loop, minedu_worker_loop)
│   │   │   └── orchestrator.py      # Gestor de threads (start/stop/pause)
│   │   └── api/
│   │       └── endpoints.py         # FastAPI routes (/api/...)
│   └── data/
│       └── registros.db             # SQLite database
│
└── FRONTENDWORKER/                  # Frontend React + Vite
    ├── src/
    ├── vite.config.js
    └── package.json
```

---

## Conexiones y Puertos

| Componente | URL | Puerto |
|---|---|---|
| **Backend (FastAPI)** | `http://127.0.0.1:8000` | `8000` |
| **Frontend (Vite/React)** | `http://localhost:3000` | `3000` |
| **SUNEDU** | `https://constanciasweb.sunedu.gob.pe` | HTTPS |
| **MINEDU** | `https://titulosinstitutos.minedu.gob.pe` | HTTPS |

### CORS
El backend acepta requests desde `http://localhost:3000` y `http://localhost:5173`.

### Frontend Proxy
El frontend (`vite.config.js`) proxea `/api` → `http://127.0.0.1:8000/api`.

---

## Cómo Ejecutar

### 1. Backend
```bash
cd webapp/BACKEND_REFACTORED
pip install -r requirements.txt
python main.py
```
> Al iniciar, el servidor **auto-recupera** DNIs atascados en estados `PROCESANDO_*` de ejecuciones previas.

### 2. Frontend
```bash
cd webapp/FRONTENDWORKER
npm install
npm run dev
```

### 3. Abrir
Navegar a `http://localhost:3000`

---

## API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/upload` | Subir Excel/CSV/TXT con DNIs (valida 8 dígitos, retorna inválidos) |
| `GET` | `/api/status` | Estado general: conteos por fase, pipeline, progreso % |
| `GET` | `/api/registros` | Lista de registros con paginación (`?estado=&lote_id=&limit=&offset=`) |
| `GET` | `/api/lotes` | Lista de lotes creados |
| `POST` | `/api/workers/start` | Iniciar workers (auto-recupera atascados antes de arrancar) |
| `POST` | `/api/workers/stop` | Detener workers completamente |
| `GET` | `/api/workers/status` | Estado de los workers (`running`, `paused`) |
| `POST` | `/api/retry` | Reintentar registros fallidos (`NOT_FOUND`, `ERROR_*` → `PENDIENTE`) |
| `POST` | `/api/recover` | Recuperar DNIs atascados en `PROCESANDO_*` manualmente |
| `GET` | `/api/resultados` | Descargar Excel (3 hojas: Todos, Sunedu, Minedu) |
| `POST` | `/api/limpiar` | Borrar todos los datos (registros + lotes) |

---

## Pipeline de Estados

```
PENDIENTE → PROCESANDO_SUNEDU → FOUND_SUNEDU ✅
                               → CHECK_MINEDU → PROCESANDO_MINEDU → FOUND_MINEDU ✅
                                                                    → NOT_FOUND ❌
                               → ERROR_SUNEDU ⚠️
                                              → ERROR_MINEDU ⚠️
```

### Recuperación de estados atascados
Si un worker se cae o el navegador se cierra inesperadamente:

| Estado atascado | Se recupera a | Cuándo |
|----------------|---------------|--------|
| `PROCESANDO_SUNEDU` | → `PENDIENTE` | Al iniciar servidor, al hacer START, o manual `/recover` |
| `PROCESANDO_MINEDU` | → `CHECK_MINEDU` | Al iniciar servidor, al hacer START, o manual `/recover` |

---

## Formato del Archivo Excel (Requisito Previo)

> ⚠️ **ANTES DE EMPEZAR**: Debes tener listo tu archivo Excel (`.xlsx`) antes de abrir el sistema.

El archivo debe ser extremadamente simple. Se recomienda una **única columna** con los números de DNI. No se requieren fórmulas ni estilos.

**Ejemplo visual de cómo debe verse tu Excel:**

| | A |
|---|---|
| **1** | **DNI** |
| **2** | 27470171 |
| **3** | 88017131 |
| **4** | 93732267 |
| **5** | 10173113 |
| **6** | 10777845 |
| **7** | ... |

- La cabecera "DNI" es opcional pero recomendada.
- El sistema detectará automáticamente la columna con los números de 8 dígitos.
- **Evita** celdas vacías entre medias o filas con texto que no sea DNI.

---

## Validación de DNIs en Importación

Al subir un archivo Excel/CSV/TXT:

- Solo se aceptan DNIs con **exactamente 8 dígitos numéricos**
- Se eliminan duplicados automáticamente
- DNIs inválidos se retornan por separado al frontend
- El frontend muestra un panel colapsable con los DNIs rechazados

**Ejemplo de respuesta `/upload`:**
```json
{
  "total_dnis": 50,
  "invalid_dnis": ["123", "abc", "1234567890"],
  "total_invalid": 3,
  "lote_id": 5
}
```

---

## Exportación Excel

El archivo descargado contiene **3 hojas**:

| Hoja | Contenido |
|------|-----------|
| **Todos** | Todos los registros del lote |
| **Sunedu** | Solo registros encontrados en SUNEDU (`FOUND_SUNEDU`) |
| **Minedu** | Solo registros encontrados en MINEDU (`FOUND_MINEDU`) |

### Formato
- **Fuente**: Aptos Narrow (tamaño 11) en todas las celdas
- **Encabezado**: Fondo gris `#D9D9D9`, texto en negrita
- **Encontrados**: Fila con fondo verde claro `#C6EFCE`
- **No encontrados / Errores**: Fila con fondo rojo claro `#FFC7CE`
- **Bordes**: Línea fina gris en todas las celdas
- **Tabla Excel nativa**: Con filtros automáticos en cada columna
- **Columnas auto-ajustadas** al ancho del contenido

### Columnas del Excel

| Columna | Fuente |
|---------|--------|
| DNI | Dato de entrada |
| Estado | Pipeline state |
| Mensaje | Error message (si aplica) |
| Sunedu_Nombres | Web SUNEDU |
| Sunedu_Grado | Web SUNEDU |
| Sunedu_Institucion | Web SUNEDU |
| Sunedu_FechaDiploma | Web SUNEDU |
| Minedu_Nombres | Web MINEDU |
| Minedu_Titulo | Web MINEDU |
| Minedu_Institucion | Web MINEDU |
| Minedu_FechaExpedicion | Web MINEDU |

---

## Scrapers

### SUNEDU (`sunedu.py`)
- **Motor**: Botasaurus (Selenium wrapper con anti-detección)
- **Flujo**:
  1. Navega a la web de SUNEDU
  2. Detecta estado (Turnstile/checkbox/tabla/swal)
  3. Pasa verificación Cloudflare Turnstile si aparece
  4. Ingresa DNI vía JavaScript (Angular reactive forms)
  5. Verifica que el campo aceptó el DNI y el botón está habilitado
  6. Click en "Buscar" con verificación de ejecución
  7. Espera resultado (tabla o modal "sin registros")
  8. Extrae datos de la tabla
- **Tiempos**:
  - Carga inicial: **6s**
  - Pre-DNI: **2s**
  - Post-Turnstile fail: **7s**
  - Post-resultado: **2s**
- **Reintentos**: 5 intentos (configurable en `SUNEDU_MAX_RETRIES`)

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
- **Tiempos**:
  - Carga página: **2s**
  - Post-click búsqueda: **3s**
  - Check resultado: **5 intentos × 1s**
- **Reintentos**: 8 intentos (configurable en `MINEDU_MAX_RETRIES`)

---

## Monitoreo Profesional del Navegador (CDP)

### ¿Qué es?
Un sistema de **instrumentación** del navegador que intercepta TODO lo que ocurre dentro de la web de SUNEDU/MINEDU, sin necesidad de tener su código fuente.

### ¿Cómo funciona?

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

### Eventos capturados

| Evento | Interceptor | Ejemplo en consola |
|---|---|---|
| `console.log/warn/error` | Override `console.*` | `[BROWSER][CONSOLE.ERROR] Failed to load resource` |
| JS Errors | `window.onerror` | `[BROWSER][JS_ERROR] Cannot read prop @ app.js:142` |
| Promise Rejections | `unhandledrejection` | `[BROWSER][PROMISE_FAIL] Network timeout` |
| HTTP 4xx/5xx | Override `fetch` + `XHR.load` | `[BROWSER][HTTP_500] POST /api/consulta` |
| Network Failures | Override `fetch.catch` + `XHR.error` | `[BROWSER][NET_FAIL] GET /api - ERR_CONNECTION` |

### Archivos
- `app/scrapers/sunedu.py` → `MONITOR_INIT_SCRIPT` + `_setup_cdp_monitoring()` + `_collect_events()`
- `app/scrapers/minedu.py` → Misma implementación

### Fallback
Si CDP no está disponible (versión de Chrome incompatible), automáticamente usa inyección post-carga como fallback.

---

## Historial de Cambios

### v1.0 — Refactorización Completa
- **Antes**: Todo en un solo archivo `workers.py` (855 líneas)
- **Después**: Separado en módulos (`scrapers/`, `workers/`, `api/`, `db/`, `core/`)

### v1.1 — Tiempos de Espera SUNEDU
| Acción | Antes | Después |
|--------|-------|---------| 
| Carga inicial | 3s | **6s** |
| Pre-DNI | 0s | **2s** |
| Turnstile fail | 2s | **7s** |
| Post-resultado | 0s | **2s** |

### v1.2 — Sincronización MINEDU con Bot Original
- Click directo (`btn.click()`) en vez de MouseEvent
- Espera post-click: **3s** (antes 0.5s)
- 5 intentos de verificación de resultado
- Tiempos de captcha y refresh ajustados

### v1.3 — Retry Logic SUNEDU Mejorada
- Eliminado bug de doble-recarga en errores
- Verificación de campo de input post-ingreso
- Verificación de botón habilitado pre-click
- Confirmación de ejecución de búsqueda post-click

### v1.4 — Validación de DNIs + Excel Profesional
- Solo se aceptan DNIs con exactamente 8 dígitos
- DNIs inválidos se muestran en panel colapsable en el frontend
- Excel con 3 hojas: Todos, Sunedu, Minedu
- Formato: Aptos Narrow, header gris, colores verde/rojo por estado
- Tabla Excel nativa con filtros y columnas auto-ajustadas

### v1.5 — Recuperación de DNIs Atascados
- Auto-recuperación en `on_startup` del servidor
- Auto-recuperación al hacer START de workers
- Endpoint manual `/recover` para recuperar PROCESANDO_*
- Botón "RECUPERAR X ATASCADOS" en frontend (aparece automáticamente)

### v1.6 — Control de Workers
- **Stop**: Termina threads completamente (`stop_workers()`) en vez de pausar
- Esto evita conexiones zombie y errores al reiniciar

### v1.7 — Logging y Monitoreo
- Excepciones usan `repr(e)` para capturar detalles completos
- Monitoreo profesional del navegador (CDP)

---

## Dependencias

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

### Node.js (Solo para Frontend)
```
react
vite
tailwindcss
```

---

## Configuración (`app/core/config.py`)

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `SUNEDU_URL` | `https://constanciasweb.sunedu.gob.pe/...` | URL de consulta SUNEDU |
| `MINEDU_URL` | `https://titulosinstitutos.minedu.gob.pe/` | URL de consulta MINEDU |
| `SUNEDU_MAX_RETRIES` | `5` | Reintentos por DNI en SUNEDU |
| `MINEDU_MAX_RETRIES` | `8` | Reintentos por DNI en MINEDU |
| `SUNEDU_SLEEP_MIN` | `3.0` | Sleep mínimo entre consultas SUNEDU |
| `SUNEDU_SLEEP_MAX` | `4.2` | Sleep máximo entre consultas SUNEDU |
| `MINEDU_SLEEP_MIN` | `1.0` | Sleep mínimo entre consultas MINEDU |
| `MINEDU_SLEEP_MAX` | `2.0` | Sleep máximo entre consultas MINEDU |
| `HEADLESS` | `False` | Mostrar navegador (True para producción) |
| `BLOCK_IMAGES_SUNEDU` | `True` | Bloquear imágenes en SUNEDU (más rápido) |
| `BLOCK_IMAGES_MINEDU` | `False` | No bloquear en MINEDU (necesita captcha) |
| `API_HOST` | `127.0.0.1` | Host del servidor |
| `API_PORT` | `8000` | Puerto del servidor |
| `WORKER_POLL_INTERVAL` | `2` | Segundos entre polling de workers |
| `WINDOW_SIZE` | `(1366, 768)` | Tamaño ventana del navegador |

---

## Solución de Problemas

| Problema | Causa | Solución |
|----------|-------|----------|
| DNIs atascados en PROCESANDO | Worker/navegador se cayó | Hacer clic en START (auto-recupera) o usar botón RECUPERAR |
| Captcha MINEDU falla siempre | OCR impreciso | El sistema reintenta automáticamente (hasta 8 veces por DNI) |
| Turnstile SUNEDU no pasa | Detección anti-bot | El sistema espera 7s y reintenta. No usar en modo `HEADLESS` |
| Chrome no abre | Chrome no instalado | Instalar Google Chrome última versión estable |
| Error de memoria | RAM insuficiente | Cerrar aplicaciones innecesarias. Mínimo 16 GB |
| Muy lento | HDD mecánico | **Usar SSD es indispensable** |
| Frontend no conecta | Backend no iniciado | Iniciar backend primero (`python main.py`) |
| `ModuleNotFoundError` | Dependencias faltantes | `pip install -r requirements.txt` |

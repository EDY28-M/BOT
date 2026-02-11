# 🎯 ESPECIFICACIÓN FRONTEND — Validador de Grados Académicos

## Descripción del Proyecto

Sistema de validación masiva de grados académicos que consulta automáticamente **SUNEDU** (universidades) y **MINEDU** (institutos) a partir de una lista de DNIs. El usuario sube un archivo Excel/CSV, el sistema procesa cada DNI en paralelo con dos workers (bots de scraping), y muestra el progreso en tiempo real.

**Backend:** API REST con FastAPI corriendo en `http://127.0.0.1:8000`  
**Base de datos:** SQLite  
**Auto-refresh:** Polling cada 2 segundos al frontend

---

## 🔌 API ENDPOINTS (Backend)

### 1. `POST /api/upload` — Subir archivo con DNIs

Sube un archivo Excel (.xlsx, .xls) o CSV con una columna llamada `DNI`, `DOCUMENTO`, `NRO_DOCUMENTO` o `NUM_DOC`.

**Request:** `multipart/form-data` con campo `file`

**Response:**
```json
{
  "lote_id": 1,
  "nombre_archivo": "lista_alumnos.xlsx",
  "total_dnis": 131,
  "mensaje": "Se cargaron 131 DNIs correctamente"
}
```

**Errores posibles:**
- 400: Formato no soportado
- 400: No se encontró columna DNI
- 400: No se encontraron DNIs válidos

---

### 2. `GET /api/status` — Métricas y estado general (⚡ POLLING PRINCIPAL)

Este es el endpoint principal que el frontend debe consultar cada 2 segundos para actualizar todo el dashboard.

**Response:**
```json
{
  "total": 131,
  "terminados": 122,
  "en_proceso": 2,
  "progreso_pct": 93.1,
  "conteos": {
    "PENDIENTE": 7,
    "PROCESANDO_SUNEDU": 1,
    "FOUND_SUNEDU": 86,
    "CHECK_MINEDU": 3,
    "PROCESANDO_MINEDU": 1,
    "FOUND_MINEDU": 25,
    "NOT_FOUND": 5,
    "ERROR_SUNEDU": 2,
    "ERROR_MINEDU": 1
  },
  "pipeline": {
    "sunedu": {
      "pendientes": 7,
      "procesando": 1,
      "encontrados": 86,
      "derivados_minedu": 3,
      "errores": 2
    },
    "minedu": {
      "pendientes": 3,
      "procesando": 1,
      "encontrados": 25,
      "no_encontrados": 5,
      "errores": 1
    }
  }
}
```

**Estados posibles de un DNI (ciclo de vida):**

```
PENDIENTE → PROCESANDO_SUNEDU → FOUND_SUNEDU (✅ encontrado en SUNEDU, fin)
                               → CHECK_MINEDU → PROCESANDO_MINEDU → FOUND_MINEDU (✅ encontrado en MINEDU, fin)
                                                                   → NOT_FOUND (❌ no encontrado en ninguno, fin)
                                                                   → ERROR_MINEDU (⚠️ error técnico, fin)
                               → ERROR_SUNEDU (⚠️ error técnico, fin)
```

---

### 3. `GET /api/workers/status` — Estado de los workers

**Response:**
```json
{
  "sunedu": {
    "name": "sunedu",
    "running": true,
    "started_at": "2026-02-10T14:30:00",
    "stopped_at": null,
    "restart_count": 0,
    "thread_id": 12345
  },
  "minedu": {
    "name": "minedu",
    "running": true,
    "started_at": "2026-02-10T14:30:01",
    "stopped_at": null,
    "restart_count": 2,
    "thread_id": 12346
  }
}
```

---

### 4. `POST /api/workers/start` — Iniciar workers

**Query param opcional:** `?worker=sunedu` o `?worker=minedu` (sin parámetro inicia ambos)

**Response (ambos):**
```json
{
  "workers": {
    "sunedu": true,
    "minedu": true
  }
}
```

**Response (uno solo):**
```json
{
  "worker": "sunedu",
  "started": true
}
```

---

### 5. `POST /api/workers/stop` — Detener workers

Misma lógica que start. Query param opcional `?worker=sunedu|minedu`.

**Response:** Igual estructura que start pero con campo `stopped`.

---

### 6. `GET /api/registros` — Listar registros con filtros

**Query params:**
- `estado` (string, opcional): Filtrar por estado (`FOUND_SUNEDU`, `FOUND_MINEDU`, `NOT_FOUND`, `ERROR_SUNEDU`, `ERROR_MINEDU`, etc.)
- `lote_id` (int, opcional): Filtrar por lote
- `limit` (int, default 500, max 5000)
- `offset` (int, default 0)

**Response:**
```json
[
  {
    "id": 1,
    "lote_id": 1,
    "dni": "12345678",
    "estado": "FOUND_SUNEDU",
    "error_msg": null,
    "created_at": "2026-02-10T14:30:00",
    "updated_at": "2026-02-10T14:31:15",
    "sunedu_nombres": "GARCIA PEREZ, JUAN CARLOS",
    "sunedu_grado": "BACHILLER EN INGENIERÍA DE SISTEMAS",
    "sunedu_institucion": "UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS",
    "sunedu_fecha_diploma": "15/07/2020"
  },
  {
    "id": 2,
    "lote_id": 1,
    "dni": "87654321",
    "estado": "FOUND_MINEDU",
    "error_msg": "No se encontró en SUNEDU - derivado a MINEDU",
    "created_at": "2026-02-10T14:30:00",
    "updated_at": "2026-02-10T14:32:45",
    "minedu_nombres": "LOPEZ TORRES, MARIA",
    "minedu_titulo": "PROFESIONAL TÉCNICO EN ENFERMERÍA",
    "minedu_institucion": "INSTITUTO SUPERIOR TECNOLÓGICO PÚBLICO",
    "minedu_fecha": "20/12/2019"
  },
  {
    "id": 3,
    "lote_id": 1,
    "dni": "11223344",
    "estado": "NOT_FOUND",
    "error_msg": "No se encontró título en MINEDU",
    "created_at": "2026-02-10T14:30:00",
    "updated_at": "2026-02-10T14:33:10"
  },
  {
    "id": 4,
    "lote_id": 1,
    "dni": "55667788",
    "estado": "ERROR_SUNEDU",
    "error_msg": "Se agotaron todos los reintentos en SUNEDU (5 intentos) | Último motivo: Falló la verificación de seguridad/captcha en SUNEDU",
    "created_at": "2026-02-10T14:30:00",
    "updated_at": "2026-02-10T14:35:00"
  }
]
```

**Campos condicionales (solo aparecen si hay datos):**
- Si `FOUND_SUNEDU`: `sunedu_nombres`, `sunedu_grado`, `sunedu_institucion`, `sunedu_fecha_diploma`
- Si `FOUND_MINEDU`: `minedu_nombres`, `minedu_titulo`, `minedu_institucion`, `minedu_fecha`
- `error_msg`: Siempre presente, contiene el **motivo** legible del resultado

---

### 7. `GET /api/lotes` — Listar lotes subidos

**Response:**
```json
[
  {
    "id": 2,
    "nombre_archivo": "segundo_lote.xlsx",
    "total_dnis": 50,
    "created_at": "2026-02-10T15:00:00"
  },
  {
    "id": 1,
    "nombre_archivo": "primer_lote.csv",
    "total_dnis": 131,
    "created_at": "2026-02-10T14:30:00"
  }
]
```

---

### 8. `GET /api/resultados` — Descargar Excel con resultados

**Query param opcional:** `?lote_id=1`

**Response:** Archivo `.xlsx` descargable con todas las columnas:
`dni, estado, sunedu_nombres, sunedu_grado, sunedu_institucion, sunedu_fecha_diploma, minedu_nombres, minedu_titulo, minedu_institucion, minedu_fecha, error_msg, lote_id, created_at, updated_at`

---

### 9. `POST /api/limpiar` — Limpiar todo (reset)

Detiene los workers y elimina todos los registros y lotes de la base de datos.

**Response:**
```json
{
  "mensaje": "Todo limpiado correctamente",
  "registros_eliminados": 131,
  "lotes_eliminados": 2
}
```

---

## 📊 VISTAS / SECCIONES QUE DEBE TENER EL FRONTEND

### SIDEBAR (Panel de Control)

| Elemento | Datos | Endpoint |
|----------|-------|----------|
| Estado Worker SUNEDU | `running: true/false`, badge ONLINE/OFFLINE, `restart_count` | `GET /api/workers/status` |
| Estado Worker MINEDU | `running: true/false`, badge ONLINE/OFFLINE, `restart_count` | `GET /api/workers/status` |
| Botón **INICIAR** | Inicia ambos workers | `POST /api/workers/start` |
| Botón **DETENER** | Detiene ambos workers | `POST /api/workers/stop` |
| Upload archivo | Subir .xlsx/.xls/.csv, muestra nombre y peso, botón procesar | `POST /api/upload` |
| Botón **LIMPIAR TODO** | Reset total del sistema | `POST /api/limpiar` |
| Toggle **Auto-refresh** | Activa/desactiva polling cada 2s | Local |
| Botón **Actualizar ahora** | Fuerza refresh manual | Local |

### MÉTRICAS EN VIVO (4 cards grandes)

| Métrica | Color | Fuente |
|---------|-------|--------|
| **Total DNIs** | Púrpura (#a855f7) | `status.total` |
| **Encontrados SUNEDU** | Verde (#00ff88) | `status.conteos.FOUND_SUNEDU` |
| **Encontrados MINEDU** | Azul (#3b82f6) | `status.conteos.FOUND_MINEDU` |
| **Sin Títulos** | Rojo (#ff4757) | `status.conteos.NOT_FOUND` |

### PIPELINE WATERFALL (2 columnas)

**Columna SUNEDU (pipeline.sunedu):**
- Barra de progreso: completados / total
- Mini cards: Pendientes, Encontrados, → MINEDU (derivados)
- Label: "SUNEDU Worker - Universidades"

**Columna MINEDU (pipeline.minedu):**
- Barra de progreso: completados / total
- Mini cards: Pendientes, Encontrados, No Encontrados
- Label: "MINEDU Worker - Institutos"

### TERMINAL DE LOGS (panel inferior izquierdo)

Consola estilo hacker/terminal que muestra mensajes dinámicos basados en el estado actual:
- `[INFO]` "Procesando DNI en SUNEDU/MINEDU..."
- `[SUCCESS]` "Encontrados X registros en SUNEDU/MINEDU"
- `[WARNING]` "X DNIs derivados de SUNEDU → MINEDU"
- `[ERROR]` "X DNIs sin título en ninguna fuente"
- `[ERROR]` "Errores SUNEDU: X (captcha/timeout/verificación)"
- `[ERROR]` "Errores MINEDU: X (captcha/timeout/OCR)"

### TABLA DE RESULTADOS (panel inferior derecho)

5 tabs filtrables:

| Tab | Endpoint | Columnas |
|-----|----------|----------|
| **Todos** | `GET /api/registros?limit=50` | dni, estado, error_msg (Motivo), updated_at, sunedu_nombres, sunedu_grado, minedu_titulo |
| **SUNEDU ✅** | `GET /api/registros?estado=FOUND_SUNEDU&limit=50` | dni, sunedu_nombres, sunedu_grado, sunedu_institucion, sunedu_fecha_diploma |
| **MINEDU ✅** | `GET /api/registros?estado=FOUND_MINEDU&limit=50` | dni, minedu_nombres, minedu_titulo, minedu_institucion, minedu_fecha |
| **No encontrados** | `GET /api/registros?estado=NOT_FOUND&limit=50` | dni, estado, error_msg (Motivo), updated_at |
| **⚠️ Errores** | `GET /api/registros?estado=ERROR_SUNEDU&limit=50` + `GET /api/registros?estado=ERROR_MINEDU&limit=50` | Resumen de errores agrupados por motivo + tabla con dni, estado (Worker), error_msg (Motivo del Error), updated_at |

### BOTÓN DESCARGAR EXCEL

Descarga un archivo Excel completo con todos los resultados.
- Endpoint: `GET /api/resultados`
- Response: archivo .xlsx

---

## 🏷️ MOTIVOS DE ERROR (campo `error_msg`)

El campo `error_msg` contiene mensajes legibles que explican **por qué** un DNI tiene cierto estado. Posibles valores:

### SUNEDU (cuando pasa a CHECK_MINEDU):
- `"No se encontró en SUNEDU - derivado a MINEDU"`
- `"Error al extraer datos de la tabla SUNEDU"`

### SUNEDU (cuando queda en ERROR_SUNEDU):
- `"Se agotaron todos los reintentos en SUNEDU (5 intentos) | Último motivo: Falló la verificación de seguridad/captcha en SUNEDU"`
- `"Se agotaron todos los reintentos en SUNEDU (5 intentos) | Último motivo: No se pasó la verificación de seguridad en SUNEDU"`
- `"Se agotaron todos los reintentos en SUNEDU (5 intentos) | Último motivo: Tiempo de espera agotado en SUNEDU - la página tardó demasiado"`
- `"Se agotaron todos los reintentos en SUNEDU (5 intentos) | Último motivo: No se encontró el botón de búsqueda en SUNEDU"`
- `"Se agotaron todos los reintentos en SUNEDU (5 intentos) | Último motivo: La página de SUNEDU no cargó correctamente: [detalle]"`

### MINEDU (cuando queda en NOT_FOUND):
- `"No se encontró título en MINEDU"`

### MINEDU (cuando queda en ERROR_MINEDU):
- `"Se agotaron todos los reintentos en MINEDU (8 intentos) | Último motivo: Falló la verificación del captcha en MINEDU"`
- `"Se agotaron todos los reintentos en MINEDU (8 intentos) | Último motivo: Captcha incorrecto en MINEDU: [detalle del error]"`
- `"Se agotaron todos los reintentos en MINEDU (8 intentos) | Último motivo: Falló el OCR del captcha en MINEDU"`
- `"Se agotaron todos los reintentos en MINEDU (8 intentos) | Último motivo: No se encontró el botón de consulta en MINEDU"`
- `"Se agotaron todos los reintentos en MINEDU (8 intentos) | Último motivo: No se pudo refrescar el captcha en MINEDU"`
- `"Se agotaron todos los reintentos en MINEDU (8 intentos) | Último motivo: Tiempo de espera agotado en MINEDU"`

---

## ⚡ FLUJO DEL PIPELINE (cómo funciona)

```
1. Usuario sube archivo Excel/CSV con DNIs
   └─→ POST /api/upload → Crea lote, todos los DNIs quedan en estado PENDIENTE

2. Workers se inician (automático o manual)
   └─→ POST /api/workers/start

3. SUNEDU Worker (hilo paralelo)
   ├─ Toma DNI en PENDIENTE → lo marca PROCESANDO_SUNEDU
   ├─ Busca en SUNEDU (3-4s por DNI encontrado, 3.6s si no encontrado)
   ├─ Si encuentra → FOUND_SUNEDU (✅ fin para ese DNI)
   ├─ Si no encuentra → CHECK_MINEDU (se deriva, MINEDU lo recoge)
   └─ Si error → ERROR_SUNEDU (con motivo detallado)

4. MINEDU Worker (hilo paralelo, corre al mismo tiempo)
   ├─ Toma DNI en CHECK_MINEDU → lo marca PROCESANDO_MINEDU
   ├─ Busca en MINEDU (1-2s entre consultas, búsqueda rápida)
   ├─ Si encuentra → FOUND_MINEDU (✅ fin)
   ├─ Si no encuentra → NOT_FOUND (❌ fin, con motivo)
   └─ Si error → ERROR_MINEDU (con motivo detallado)

5. Frontend hace polling cada 2s a GET /api/status para actualizar todo
```

Los dos workers corren **en paralelo**: mientras SUNEDU busca un DNI, MINEDU puede estar buscando otro que ya fue derivado. MINEDU tiene un polling cada 2 segundos para recoger DNIs nuevos que SUNEDU va derivando.

---

## 🎨 SUGERENCIAS DE DISEÑO

- **Theme:** Dark mode / Cyberpunk
- **Colores:** Fondo oscuro (#0a0a0f), verde neón (#00ff88) para éxito, cyan (#00d4ff) para info, rojo (#ff4757) para errores, púrpura (#a855f7) para totales, azul (#3b82f6) para MINEDU
- **Badges:** Los workers deben mostrar ONLINE (verde pulsante) / OFFLINE (rojo)
- **Progreso:** Barras de progreso animadas con shimmer/glow para cada worker
- **Métricas:** Cards grandes con números que se actualizan en tiempo real y el número principal destaque bastante 
- **Tabla:** Data table con filtros por tabs, columna "Motivo" siempre visible
- **Terminal:** Panel de logs estilo consola/terminal con timestamps y colores por nivel (INFO=cyan, SUCCESS=verde, ERROR=rojo, WARNING=amarillo)
- **Responsive:** El sidebar puede colapsarse en mobile
- **Glassmorphism:** Contenedores con blur y bordes semi-transparentes

"""
API REST con FastAPI.

Endpoints:
  POST /api/upload         → Subir Excel con DNIs
  GET  /api/status         → Conteos por estado
  GET  /api/lotes          → Listar lotes
  GET  /api/registros      → Listar registros (con filtros)
  GET  /api/resultados     → Descargar Excel con resultados
  POST /api/workers/start  → Iniciar workers
  POST /api/workers/stop   → Detener workers
  GET  /api/workers/status → Estado de workers
"""
import io
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from config import Estado
from database import (
    crear_lote, obtener_conteos, obtener_total,
    obtener_registros, obtener_lotes, init_db,
    limpiar_todo, reintentar_no_encontrados,
    hay_trabajo_pendiente, contar_retryables,
    recuperar_procesando,
)
from orchestrator import Orchestrator

from config import Estado

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("API")

app = FastAPI(
    title="Validador de Grados Académicos",
    description="Pipeline SUNEDU → MINEDU para validación masiva de DNIs",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()

# ── Static files & dashboard ──
# React build output (npm run build → ../static/dist)
DIST_DIR = Path(__file__).parent / "static" / "dist"
# Fallback to old static dir
STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
async def serve_dashboard():
    """Serve the React SPA index.html (production build)."""
    index = DIST_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    # Fallback to legacy static/index.html
    return FileResponse(STATIC_DIR / "index.html")


# ═══════════════════════════════════════════════════════════════════════
#  UPLOAD
# ═══════════════════════════════════════════════════════════════════════

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Sube un archivo Excel/CSV con una columna 'DNI' o 'DOCUMENTO'.
    Crea un lote y los registros en estado PENDIENTE.
    """
    filename = file.filename or "archivo"
    log.info(f"[UPLOAD] Recibido: {filename}")

    content = await file.read()
    try:
        if filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content), dtype=str)
        elif filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), dtype=str)
        else:
            raise HTTPException(400, "Formato no soportado. Use .xlsx, .xls o .csv")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Error leyendo archivo: {e}")

    # Buscar columna de DNI
    dni_col = None
    for col in df.columns:
        if col.strip().upper() in ("DNI", "DOCUMENTO", "NRO_DOCUMENTO", "NUM_DOC"):
            dni_col = col
            break

    if dni_col is None:
        cols = ", ".join(df.columns.tolist())
        raise HTTPException(
            400,
            f"No se encontró columna 'DNI' o 'DOCUMENTO'. Columnas encontradas: {cols}",
        )

    dnis = df[dni_col].dropna().astype(str).str.strip().tolist()
    dnis = [d for d in dnis if d.isdigit() and len(d) >= 7]

    if not dnis:
        raise HTTPException(400, "No se encontraron DNIs válidos en el archivo")

    lote = crear_lote(filename, dnis)

    log.info(f"[UPLOAD] Lote {lote.id} creado con {lote.total_dnis} DNIs")
    return {
        "lote_id": lote.id,
        "nombre_archivo": filename,
        "total_dnis": lote.total_dnis,
        "mensaje": f"Se cargaron {lote.total_dnis} DNIs correctamente",
    }


# ═══════════════════════════════════════════════════════════════════════
#  STATUS / MÉTRICAS
# ═══════════════════════════════════════════════════════════════════════

@app.get("/api/status")
def get_status():
    """Retorna conteos de registros por estado y métricas generales."""
    conteos = obtener_conteos()
    total = obtener_total()

    # Calcular progreso
    terminados = sum(
        conteos.get(e, 0) for e in Estado.TERMINALES
    )
    en_proceso = sum(
        conteos.get(e, 0)
        for e in [Estado.PROCESANDO_SUNEDU, Estado.PROCESANDO_MINEDU]
    )
    pendientes_sunedu = conteos.get(Estado.PENDIENTE, 0) + conteos.get(Estado.PROCESANDO_SUNEDU, 0)
    pendientes_minedu = conteos.get(Estado.CHECK_MINEDU, 0) + conteos.get(Estado.PROCESANDO_MINEDU, 0)

    # Retry info
    retryables = contar_retryables()
    hay_pendiente = hay_trabajo_pendiente()
    pipeline_idle = not hay_pendiente and total > 0

    return {
        "total": total,
        "terminados": terminados,
        "en_proceso": en_proceso,
        "progreso_pct": round(terminados / total * 100, 1) if total > 0 else 0,
        "conteos": conteos,
        "pipeline": {
            "sunedu": {
                "pendientes": conteos.get(Estado.PENDIENTE, 0),
                "procesando": conteos.get(Estado.PROCESANDO_SUNEDU, 0),
                "encontrados": conteos.get(Estado.FOUND_SUNEDU, 0),
                "derivados_minedu": conteos.get(Estado.CHECK_MINEDU, 0),
                "errores": conteos.get(Estado.ERROR_SUNEDU, 0),
            },
            "minedu": {
                "pendientes": conteos.get(Estado.CHECK_MINEDU, 0),
                "procesando": conteos.get(Estado.PROCESANDO_MINEDU, 0),
                "encontrados": conteos.get(Estado.FOUND_MINEDU, 0),
                "no_encontrados": conteos.get(Estado.NOT_FOUND, 0),
                "errores": conteos.get(Estado.ERROR_MINEDU, 0),
            },
        },
        "retry": {
            "retryables": retryables,
            "pipeline_idle": pipeline_idle,
            "can_retry": pipeline_idle and retryables > 0,
        },
    }


@app.get("/api/lotes")
def get_lotes():
    """Lista todos los lotes subidos."""
    return obtener_lotes()


@app.get("/api/registros")
def get_registros(
    estado: Optional[str] = Query(None),
    lote_id: Optional[int] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
):
    """Lista registros con filtros opcionales."""
    return obtener_registros(estado=estado, lote_id=lote_id, limit=limit, offset=offset)


# ═══════════════════════════════════════════════════════════════════════
#  DESCARGA DE RESULTADOS
# ═══════════════════════════════════════════════════════════════════════

@app.get("/api/resultados")
def download_resultados(lote_id: Optional[int] = Query(None)):
    """Descarga un Excel con todos los resultados."""
    registros = obtener_registros(lote_id=lote_id, limit=50000)

    if not registros:
        raise HTTPException(404, "No hay resultados para descargar")

    df = pd.DataFrame(registros)

    # Reordenar columnas
    cols_orden = [
        "dni", "estado",
        "sunedu_nombres", "sunedu_grado", "sunedu_institucion", "sunedu_fecha_diploma",
        "minedu_nombres", "minedu_titulo", "minedu_institucion", "minedu_fecha",
        "error_msg", "lote_id", "created_at", "updated_at",
    ]
    cols_presentes = [c for c in cols_orden if c in df.columns]
    cols_extra = [c for c in df.columns if c not in cols_orden]
    df = df[cols_presentes + cols_extra]

    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=resultados_validacion.xlsx"},
    )


# ═══════════════════════════════════════════════════════════════════════
#  CONTROL DE WORKERS
# ═══════════════════════════════════════════════════════════════════════

@app.post("/api/workers/start")
def start_workers(worker: Optional[str] = Query(None, description="'sunedu', 'minedu' o vacío para ambos")):
    """Inicia workers. Sin parámetro inicia ambos."""
    # Recuperar DNIs atrapados en PROCESANDO_* (por stop brusco o crash)
    rec = recuperar_procesando()
    if rec["sunedu_recuperados"] + rec["minedu_recuperados"] > 0:
        log.info(f"[START] Recuperados {rec['sunedu_recuperados']} SUNEDU + {rec['minedu_recuperados']} MINEDU registros atrapados")

    if worker:
        if worker not in ("sunedu", "minedu"):
            raise HTTPException(400, "Worker debe ser 'sunedu' o 'minedu'")
        ok = orchestrator.start_worker(worker)
        return {"worker": worker, "started": ok}
    else:
        results = orchestrator.start_all()
        return {"workers": results}


@app.post("/api/workers/stop")
def stop_workers(worker: Optional[str] = Query(None)):
    """Detiene workers."""
    if worker:
        if worker not in ("sunedu", "minedu"):
            raise HTTPException(400, "Worker debe ser 'sunedu' o 'minedu'")
        ok = orchestrator.stop_worker(worker)
        return {"worker": worker, "stopped": ok}
    else:
        results = orchestrator.stop_all()
        return {"workers": results}


@app.get("/api/workers/status")
def workers_status():
    """Estado detallado de los workers."""
    return orchestrator.status()


# ═══════════════════════════════════════════════════════════════════════
#  RETRY — Re-buscar NOT_FOUND y ERRORES
# ═══════════════════════════════════════════════════════════════════════

@app.post("/api/retry")
def retry_not_found():
    """
    Re-encola los registros NOT_FOUND y ERROR_* de vuelta a PENDIENTE
    para que pasen otra vez por SUNEDU → MINEDU (una sola pasada).
    Sin límite — el usuario controla cuántas veces pulsa el botón.
    """
    # Verificar si hay trabajo pendiente aún
    if hay_trabajo_pendiente():
        raise HTTPException(
            400,
            "Aún hay registros en proceso. Espere a que terminen antes de reintentar.",
        )

    resultado = reintentar_no_encontrados()

    if resultado["reencolados"] == 0:
        return {
            "mensaje": "No hay registros para reintentar",
            **resultado,
        }

    log.info(f"[RETRY] Re-encolados {resultado['reencolados']} registros para reintento")

    # Auto-iniciar workers si no están corriendo
    any_running = any(
        info.is_running for info in orchestrator.workers.values()
    )
    if not any_running:
        orchestrator.start_all()
        log.info("[RETRY] Workers reiniciados automáticamente")

    return {
        "mensaje": f"Se re-encolaron {resultado['reencolados']} registros para nueva búsqueda",
        "workers_started": not any_running,
        **resultado,
    }


# ═══════════════════════════════════════════════════════════════════════
#  LIMPIAR TODO
# ═══════════════════════════════════════════════════════════════════════

@app.post("/api/limpiar")
def limpiar_datos():
    """Detiene workers y elimina todos los registros y lotes."""
    # Primero detener workers si están corriendo
    orchestrator.stop_all()
    log.info("[LIMPIAR] Workers detenidos")

    # Eliminar todos los datos
    resultado = limpiar_todo()
    log.info(f"[LIMPIAR] Eliminados {resultado['registros_eliminados']} registros y {resultado['lotes_eliminados']} lotes")

    return {
        "mensaje": "Todo limpiado correctamente",
        **resultado,
    }


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

# Mount static files (after all API routes)
# Serve React build assets first, then fallback static
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    from config import API_HOST, API_PORT

    init_db()
    log.info(f"[API] Iniciando en http://{API_HOST}:{API_PORT}")
    log.info(f"[API] Dashboard en http://{API_HOST}:{API_PORT}/")
    log.info(f"[API] Docs en http://{API_HOST}:{API_PORT}/docs")
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")

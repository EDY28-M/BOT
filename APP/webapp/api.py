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
from typing import Optional

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import Estado
from database import (
    crear_lote, obtener_conteos, obtener_total,
    obtener_registros, obtener_lotes, init_db,
)
from orchestrator import Orchestrator

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
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    from config import API_HOST, API_PORT

    init_db()
    log.info(f"[API] Iniciando en http://{API_HOST}:{API_PORT}")
    log.info("[API] Documentación en http://{API_HOST}:{API_PORT}/docs")
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")

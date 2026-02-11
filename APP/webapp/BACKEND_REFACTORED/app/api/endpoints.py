
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Optional

from app.db.repository import DniRepository
from app.services.excel_service import ExcelService
from app.services.retry_service import RetryService
from app.workers.orchestrator import orchestrator
from app.workers.loops import sunedu_worker_loop, minedu_worker_loop
from app.core.config import Estado

router = APIRouter()
repo = DniRepository()
retry_service = RetryService()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls', '.csv', '.txt')):
        raise HTTPException(400, "Formato no soportado")
    
    try:
        content = file.file
        cleaned_dnis = ExcelService.parse_uploaded_file(content, file.filename)
        if not cleaned_dnis:
            raise HTTPException(400, "No se encontraron DNIs válidos")
        
        lote = repo.crear_lote(file.filename, cleaned_dnis)
        return {"message": "Archivo procesado", "lote_id": lote.id, "total": lote.total_dnis}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/status")
def get_status():
    counts = repo.obtener_conteos()
    total = repo.obtener_total()
    
    # Calculate derived metrics
    pendientes = counts.get(Estado.PENDIENTE, 0)
    
    sunedu_processing = counts.get(Estado.PROCESANDO_SUNEDU, 0)
    minedu_processing = counts.get(Estado.PROCESANDO_MINEDU, 0)
    en_proceso = sunedu_processing + minedu_processing
    
    found_sunedu = counts.get(Estado.FOUND_SUNEDU, 0)
    found_minedu = counts.get(Estado.FOUND_MINEDU, 0)
    not_found = counts.get(Estado.NOT_FOUND, 0)
    error_sunedu = counts.get(Estado.ERROR_SUNEDU, 0)
    error_minedu = counts.get(Estado.ERROR_MINEDU, 0)
    
    terminados = found_sunedu + found_minedu + not_found + error_sunedu + error_minedu
    
    progreso_pct = 0
    if total > 0:
        progreso_pct = round((terminados / total) * 100, 1)

    # Pipeline logic
    check_minedu = counts.get(Estado.CHECK_MINEDU, 0)
    
    # Derivados a Minedu = Todos los que pasaron por Sunedu y no quedaron ahí
    # Es decir: CheckMinedu + ProcessingMinedu + FoundMinedu + NotFound + ErrorMinedu
    derivados_minedu = (
        check_minedu + minedu_processing + 
        found_minedu + not_found + error_minedu
    )

    pipeline = {
        "sunedu": {
            "pendientes": pendientes,
            "procesando": sunedu_processing,
            "encontrados": found_sunedu,
            "errores": error_sunedu,
            "derivados_minedu": derivados_minedu
        },
        "minedu": {
            "pendientes": check_minedu,
            "procesando": minedu_processing,
            "encontrados": found_minedu,
            "no_encontrados": not_found,
            "errores": error_minedu
        }
    }

    retryables = repo.contar_retryables()
    
    return {
        "total": total,
        "terminados": terminados,
        "en_proceso": en_proceso,
        "progreso_pct": progreso_pct,
        "conteos": counts,
        "pipeline": pipeline,
        "retry": {
            "retryables": retryables,
            "pipeline_idle": en_proceso == 0,
            "can_retry": retryables > 0
        },
        "workers": {
            "sunedu": {"running": orchestrator.is_running()}, 
            "minedu": {"running": orchestrator.is_running()}
        }
    }

@router.get("/registros")
def get_registros(
    estado: Optional[str] = None,
    lote_id: Optional[int] = None,
    limit: int = 200,
    offset: int = 0
):
    data = repo.obtener_registros(estado, lote_id, limit, offset)
    return data

@router.get("/lotes")
def get_lotes():
    return repo.obtener_lotes()

# --- Worker Control ---

@router.post("/workers/start")
def start_workers(background_tasks: BackgroundTasks):
    if orchestrator.is_running():
        orchestrator.resume_workers()
        return {"message": "Workers reanudados"}
    
    # Start threads
    # Podemos lanzar N threads de cada tipo si quisiéramos escalar
    targets = [sunedu_worker_loop, minedu_worker_loop] 
    orchestrator.start_workers(targets)
    return {"message": "Workers iniciados"}

@router.post("/workers/stop")
def stop_workers():
    orchestrator.stop_workers()
    return {"message": "Workers detenidos"}

@router.get("/workers/status")
def worker_status():
    return {
        "running": orchestrator.is_running(),
        "paused": orchestrator.is_paused()
    }

@router.post("/retry")
def retry_failed():
    count = retry_service.retry_failed()
    return {"message": f"Reencolados {count} registros"}

@router.post("/limpiar")
def limpiar_db():
    res = repo.limpiar_todo()
    return {"message": "Base de datos limpia", "detalle": res}

@router.get("/resultados")
def exportar_excel(lote_id: Optional[int] = Query(None)):
    data = repo.obtener_registros(lote_id=lote_id, limit=100000)
    if not data:
        raise HTTPException(404, "No hay datos para exportar")
    
    # Flatten/Format for Excel
    rows = []
    for r in data:
        row = {
            "DNI": r["dni"],
            "Estado": r["estado"],
            "Mensaje": r.get("error_msg", ""),
            "Sunedu_Nombres": r.get("sunedu_nombres", ""),
            "Sunedu_Grado": r.get("sunedu_grado", ""),
            "Sunedu_Institucion": r.get("sunedu_institucion", ""),
            "Sunedu_FechaDiploma": r.get("sunedu_fecha_diploma", ""),
            "Minedu_Nombres": r.get("minedu_nombres", ""),
            "Minedu_Titulo": r.get("minedu_titulo", ""),
            "Minedu_Institucion": r.get("minedu_institucion", ""),
            "Minedu_FechaExpedicion": r.get("minedu_fecha", ""),
        }
        rows.append(row)

    excel_io = ExcelService.generate_excel(rows)
    return StreamingResponse(
        excel_io, 
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment; filename=resultados.xlsx"}
    )

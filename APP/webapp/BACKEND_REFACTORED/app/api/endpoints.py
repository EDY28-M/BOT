
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Query, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Optional
import logging

from app.db.repository import DniRepository
from app.services.excel_service import ExcelService
from app.services.retry_service import RetryService
from app.workers.orchestrator import Orchestrator
from app.workers.loops import sunedu_worker_loop, minedu_worker_loop
from app.core.config import Estado
from app.core.session_manager import session_manager
from app.api.dependencies import get_session_id

log = logging.getLogger("API")

router = APIRouter()
repo = DniRepository()
retry_service = RetryService()

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Depends(get_session_id),
):
    if not file.filename.endswith(('.xlsx', '.xls', '.csv', '.txt')):
        raise HTTPException(400, "Formato no soportado")
    
    try:
        content = file.file
        result = ExcelService.parse_uploaded_file(content, file.filename)
        valid_dnis = result["valid"]
        invalid_dnis = result["invalid"]
        
        if not valid_dnis and not invalid_dnis:
            raise HTTPException(400, "No se encontraron DNIs en el archivo")
        
        lote = None
        if valid_dnis:
            lote = repo.crear_lote(session_id, file.filename, valid_dnis)
        
        return {
            "message": "Archivo procesado",
            "lote_id": lote.id if lote else None,
            "total_dnis": len(valid_dnis),
            "invalid_dnis": invalid_dnis,
            "total_invalid": len(invalid_dnis)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/status")
def get_status(session_id: str = Depends(get_session_id)):
    counts = repo.obtener_conteos(session_id)
    total = repo.obtener_total(session_id)
    
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

    retryables = repo.contar_retryables(session_id)
    
    # Worker status es POR SESION
    session_running = session_manager.session_has_running_workers(session_id)
    
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
            "sunedu": {"running": session_running}, 
            "minedu": {"running": session_running}
        }
    }

@router.get("/registros")
def get_registros(
    estado: Optional[str] = None,
    lote_id: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
    session_id: str = Depends(get_session_id),
):
    data = repo.obtener_registros(session_id, estado, lote_id, limit, offset)
    return data

@router.get("/lotes")
def get_lotes(session_id: str = Depends(get_session_id)):
    return repo.obtener_lotes(session_id)

# --- Worker Control ---

@router.post("/workers/start")
def start_workers(session_id: str = Depends(get_session_id)):
    # Recuperar DNIs atascados de esta sesión antes de iniciar
    recovered = repo.recuperar_procesando(session_id)
    total_rec = recovered.get("sunedu_recuperados", 0) + recovered.get("minedu_recuperados", 0)
    if total_rec > 0:
        log.warning(f"[{session_id[:8]}] Recuperados {total_rec} DNIs atascados: {recovered}")
    
    # Verificar si ya tiene workers
    if session_manager.session_has_running_workers(session_id):
        orch = session_manager.get_orchestrator(session_id)
        if orch:
            orch.resume_workers()
        return {"message": "Workers reanudados", "recovered": total_rec}
    
    # Verificar capacidad global
    if not session_manager.can_start_workers(2):
        stats = session_manager.get_stats()
        raise HTTPException(
            503,
            f"Capacidad del servidor alcanzada ({stats['total_workers']}/{stats['max_workers']} workers activos). "
            f"Intente más tarde."
        )
    
    # Crear orchestrator para esta sesión
    orch = Orchestrator(session_id)
    session_manager.set_orchestrator(session_id, orch)
    
    # Start threads
    targets = [sunedu_worker_loop, minedu_worker_loop]
    orch.start_workers(targets)
    
    # Registrar workers globalmente
    session_manager.register_workers(session_id, 2)
    
    return {"message": "Workers iniciados", "recovered": total_rec}

@router.post("/workers/stop")
def stop_workers(session_id: str = Depends(get_session_id)):
    orch = session_manager.get_orchestrator(session_id)
    if orch:
        orch.stop_workers()
        session_manager.unregister_workers(session_id)
    return {"message": "Workers detenidos"}

@router.get("/workers/status")
def worker_status(session_id: str = Depends(get_session_id)):
    orch = session_manager.get_orchestrator(session_id)
    return {
        "running": orch.is_running() if orch else False,
        "paused": orch.is_paused() if orch else False,
        "sunedu": {"running": orch.is_running() if orch else False},
        "minedu": {"running": orch.is_running() if orch else False},
    }

@router.post("/retry")
def retry_failed(session_id: str = Depends(get_session_id)):
    count = retry_service.retry_failed(session_id)
    return {"message": f"Reencolados {count} registros", "reencolados": count}

@router.post("/recover")
def recover_stuck(session_id: str = Depends(get_session_id)):
    """Recupera DNIs atascados en PROCESANDO_* de esta sesión."""
    result = repo.recuperar_procesando(session_id)
    total = result.get("sunedu_recuperados", 0) + result.get("minedu_recuperados", 0)
    return {"message": f"Recuperados {total} DNIs atascados", "detalle": result}

@router.post("/limpiar")
def limpiar_db(session_id: str = Depends(get_session_id)):
    # Detener workers si están corriendo
    orch = session_manager.get_orchestrator(session_id)
    if orch and orch.is_running():
        orch.stop_workers()
        session_manager.unregister_workers(session_id)
    
    res = repo.limpiar_todo(session_id)
    return {"message": "Base de datos limpia", "detalle": res}

@router.get("/resultados")
def exportar_excel(
    lote_id: Optional[int] = Query(None),
    session_id: str = Depends(get_session_id),
):
    data = repo.obtener_registros(session_id, lote_id=lote_id, limit=100000)
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

@router.get("/server/stats")
def server_stats():
    """Estadísticas globales del servidor (no requiere sesión)."""
    return session_manager.get_stats()

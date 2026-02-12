
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router
from app.db.session import init_db
from app.db.repository import DniRepository
from app.core.config import API_PORT, API_HOST
from app.core.session_manager import session_manager
import logging
import asyncio

log = logging.getLogger("STARTUP")

app = FastAPI(title="SICGTD — Sistema de Consulta de Grados y Títulos")

# CORS
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.on_event("startup")
def on_startup():
    init_db()
    
    # Migrar registros existentes sin session_id
    repo = DniRepository()
    try:
        migrated = repo.migrate_legacy_records()
        if migrated.get("registros_migrados", 0) > 0 or migrated.get("lotes_migrados", 0) > 0:
            log.warning(f"[STARTUP] Migración legacy: {migrated}")
    except Exception as e:
        log.warning(f"[STARTUP] Migración legacy omitida (columna ya existe o DB vacía): {e}")
    
    # Auto-recuperar DNIs atascados en PROCESANDO_* de TODAS las sesiones
    recovered = repo.recuperar_procesando()  # session_id=None → todas
    total = recovered.get("sunedu_recuperados", 0) + recovered.get("minedu_recuperados", 0)
    if total > 0:
        log.warning(f"[STARTUP] Recuperados {total} DNIs atascados: {recovered}")
    else:
        log.info("[STARTUP] No hay DNIs atascados en PROCESANDO")

    log.info("[STARTUP] SICGTD Backend listo — Multi-sesión activo")


async def cleanup_loop():
    """Limpia sesiones idle cada 5 minutos."""
    while True:
        await asyncio.sleep(300)
        try:
            cleaned = session_manager.cleanup_idle_sessions()
            if cleaned > 0:
                log.info(f"[CLEANUP] {cleaned} sesiones idle eliminadas")
        except Exception as e:
            log.error(f"[CLEANUP] Error: {e}")


@app.on_event("startup")
async def start_cleanup_task():
    asyncio.create_task(cleanup_loop())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=True)


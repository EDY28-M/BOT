
import time
import logging
import traceback
from botasaurus.browser import browser, Driver

from app.core.config import (
    Estado, 
    SUNEDU_SLEEP_MIN, SUNEDU_SLEEP_MAX, 
    MINEDU_SLEEP_MIN, MINEDU_SLEEP_MAX,
    WORKER_POLL_INTERVAL, HEADLESS, 
    BLOCK_IMAGES_SUNEDU, BLOCK_IMAGES_MINEDU,
    WINDOW_SIZE
)
from app.db.repository import DniRepository
from app.scrapers.sunedu import SuneduScraper, Motivo as MotivoSunedu
from app.scrapers.minedu import MineduScraper, Motivo as MotivoMinedu
from app.core.session_manager import session_manager

log = logging.getLogger("WORKER")

# --- Funciones de Loop ---

def _get_session_orchestrator(session_id: str):
    """Obtiene el orchestrator de la sesión para verificar stop/pause."""
    return session_manager.get_orchestrator(session_id)


def sunedu_worker_loop(session_id: str):
    """Entry point SUNEDU — crea Chrome fresco cada vez."""

    @browser(
        headless=HEADLESS,
        block_images=BLOCK_IMAGES_SUNEDU,
        window_size=WINDOW_SIZE,
        reuse_driver=False,
        output=None,
    )
    def _run(driver: Driver, data):
        try:
            d = getattr(driver, '_driver', None) or getattr(driver, 'driver', None)
            if d:
                d.set_window_position(-2400, -2400)
        except Exception:
            pass

        sid = data
        repo = DniRepository()
        scraper = SuneduScraper()
        orch = _get_session_orchestrator(sid)
        
        log.info(f"[{sid[:8]}] Iniciando Worker SUNEDU")
        
        while orch and not orch.stop_event.is_set():
            orch.pause_event.wait()
            if orch.stop_event.is_set():
                break
            
            try:
                item = repo.tomar_siguiente(sid, Estado.PENDIENTE, Estado.PROCESANDO_SUNEDU)
                if not item:
                    time.sleep(WORKER_POLL_INTERVAL)
                    continue

                dni = item["dni"]
                log.info(f"[{sid[:8]}][SUNEDU] Procesando {dni}...")
                
                resultado = scraper.procesar_dni(driver, dni)
                
                if resultado["encontrado"]:
                    repo.actualizar_resultado(
                        item["id"], 
                        Estado.FOUND_SUNEDU, 
                        payload_sunedu=resultado["datos"],
                        error_msg=None
                    )
                    log.info(f"[{sid[:8]}][SUNEDU] Encontrado {dni}")
                    time.sleep(2)
                else:
                    repo.actualizar_resultado(
                        item["id"],
                        Estado.CHECK_MINEDU,
                        error_msg=resultado["motivo"]
                    )
                    log.info(f"[{sid[:8]}][SUNEDU] No encontrado {dni} -> MINEDU")
                    time.sleep(2)

            except Exception as e:
                if "item" in locals() and item:
                    repo.actualizar_resultado(
                        item["id"],
                        Estado.ERROR_SUNEDU,
                        error_msg=f"Error Worker: {str(e)}"
                    )
                    log.error(f"[{sid[:8]}][SUNEDU] Error procesando {dni}: {e}")
                else:
                    log.error(f"[{sid[:8]}][SUNEDU] Loop Error: {e}")
                    time.sleep(5)

        log.info(f"[{sid[:8]}] Worker SUNEDU terminado — Chrome cerrado")

    _run(session_id)


def minedu_worker_loop(session_id: str):
    """Entry point MINEDU — crea Chrome fresco cada vez."""

    @browser(
        headless=HEADLESS,
        block_images=BLOCK_IMAGES_MINEDU,
        window_size=WINDOW_SIZE,
        reuse_driver=False,
        output=None,
    )
    def _run(driver: Driver, data):
        try:
            d = getattr(driver, '_driver', None) or getattr(driver, 'driver', None)
            if d:
                d.set_window_position(-2400, -2400)
        except Exception:
            pass

        sid = data
        repo = DniRepository()
        scraper = MineduScraper()
        orch = _get_session_orchestrator(sid)
        
        log.info(f"[{sid[:8]}] Iniciando Worker MINEDU")
        
        while orch and not orch.stop_event.is_set():
            orch.pause_event.wait()
            if orch.stop_event.is_set():
                break
            
            try:
                item = repo.tomar_siguiente(sid, Estado.CHECK_MINEDU, Estado.PROCESANDO_MINEDU)
                if not item:
                    time.sleep(WORKER_POLL_INTERVAL)
                    continue

                dni = item["dni"]
                log.info(f"[{sid[:8]}][MINEDU] Procesando {dni}...")
                
                resultado = scraper.procesar_dni(driver, dni)
                
                if resultado["encontrado"]:
                    repo.actualizar_resultado(
                        item["id"], 
                        Estado.FOUND_MINEDU, 
                        payload_minedu=resultado["datos"],
                        error_msg=None
                    )
                    log.info(f"[{sid[:8]}][MINEDU] Encontrado {dni}")
                else:
                    repo.actualizar_resultado(
                        item["id"],
                        Estado.NOT_FOUND,
                        error_msg=resultado["motivo"]
                    )
                    log.info(f"[{sid[:8]}][MINEDU] No encontrado final {dni}")

            except Exception as e:
                if "item" in locals() and item:
                    repo.actualizar_resultado(
                        item["id"],
                        Estado.ERROR_MINEDU,
                        error_msg=f"Error Worker: {str(e)}"
                    )
                    log.error(f"[{sid[:8]}][MINEDU] Error procesando {dni}: {e}")
                else:
                    log.error(f"[{sid[:8]}][MINEDU] Loop Error: {e}")
                    time.sleep(5)

        log.info(f"[{sid[:8]}] Worker MINEDU terminado — Chrome cerrado")

    _run(session_id)


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
from app.workers.orchestrator import orchestrator

log = logging.getLogger("WORKER")

# --- Funciones de Loop ---

@browser(
    headless=HEADLESS,
    block_images=BLOCK_IMAGES_SUNEDU,
    window_size=WINDOW_SIZE,
    reuse_driver=True,
    output=None,
)
def sunedu_worker_loop(driver: Driver, data):
    """Loop infinito para procesar PENDIENTE -> SUNEDU."""
    repo = DniRepository()
    scraper = SuneduScraper()
    
    log.info("Iniciando Worker SUNEDU")
    
    while not orchestrator.stop_event.is_set():
        orchestrator.pause_event.wait()
        
        try:
            # 1. Tomar siguiente
            item = repo.tomar_siguiente(Estado.PENDIENTE, Estado.PROCESANDO_SUNEDU)
            if not item:
                time.sleep(WORKER_POLL_INTERVAL)
                continue

            dni = item["dni"]
            log.info(f"[SUNEDU] Procesando {dni}...")
            
            # 2. Scrapear
            resultado = scraper.procesar_dni(driver, dni)
            
            # 3. Guardar resultado
            if resultado["encontrado"]:
                repo.actualizar_resultado(
                    item["id"], 
                    Estado.FOUND_SUNEDU, 
                    payload_sunedu=resultado["datos"],
                    error_msg=None
                )
                log.info(f"[SUNEDU] Encontrado {dni}")
                driver.short_random_sleep()
            else:
                # No encontrado -> Pasa a Minedu
                repo.actualizar_resultado(
                    item["id"],
                    Estado.CHECK_MINEDU,
                    error_msg=resultado["motivo"]
                )
                log.info(f"[SUNEDU] No encontrado {dni} -> MINEDU")

        except Exception as e:
            if "item" in locals() and item:
                 # Manejo de error
                es_error_fatal = False # Podríamos definir fatales
                nuevo_estado = Estado.ERROR_SUNEDU
                
                # Si es un error recuperable (e.g. red), quizás reintentar
                # Aquí simplificamos a ERROR_SUNEDU, el usuario puede dar Retry
                repo.actualizar_resultado(
                    item["id"],
                    nuevo_estado,
                    error_msg=f"Error Worker: {str(e)}"
                )
                log.error(f"[SUNEDU] Error procesando {dni}: {e}")
                # driver.get("about:blank") # Reset page on error
            else:
                 log.error(f"[SUNEDU] Loop Error: {e}")
                 time.sleep(5)

@browser(
    headless=HEADLESS,
    block_images=BLOCK_IMAGES_MINEDU, # Minedu usa captcha visual, no bloquear imagenes si carga el captcha como img
    window_size=WINDOW_SIZE,
    reuse_driver=True,
    output=None,
)
def minedu_worker_loop(driver: Driver, data):
    """Loop infinito para procesar CHECK_MINEDU -> MINEDU."""
    repo = DniRepository()
    scraper = MineduScraper()
    
    log.info("Iniciando Worker MINEDU")
    
    while not orchestrator.stop_event.is_set():
        orchestrator.pause_event.wait()
        
        try:
            item = repo.tomar_siguiente(Estado.CHECK_MINEDU, Estado.PROCESANDO_MINEDU)
            if not item:
                time.sleep(WORKER_POLL_INTERVAL)
                continue

            dni = item["dni"]
            log.info(f"[MINEDU] Procesando {dni}...")
            
            resultado = scraper.procesar_dni(driver, dni)
            
            if resultado["encontrado"]:
                repo.actualizar_resultado(
                    item["id"], 
                    Estado.FOUND_MINEDU, 
                    payload_minedu=resultado["datos"],
                    error_msg=None
                )
                log.info(f"[MINEDU] Encontrado {dni}")
            else:
                repo.actualizar_resultado(
                    item["id"],
                    Estado.NOT_FOUND,
                    error_msg=resultado["motivo"]
                )
                log.info(f"[MINEDU] No encontrado final {dni}")

        except Exception as e:
            if "item" in locals() and item:
                repo.actualizar_resultado(
                    item["id"],
                    Estado.ERROR_MINEDU,
                    error_msg=f"Error Worker: {str(e)}"
                )
                log.error(f"[MINEDU] Error procesando {dni}: {e}")
            else:
                 log.error(f"[MINEDU] Loop Error: {e}")
                 time.sleep(5)

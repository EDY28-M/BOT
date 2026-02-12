
import threading
import time
import logging
from typing import List

log = logging.getLogger("ORCHESTRATOR")

class Orchestrator:
    """Orchestrator por sesión — cada sesión tiene su instancia."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()  # Start unpaused (set = running)
        self.threads: List[threading.Thread] = []

    def start_workers(self, targets: List[callable]):
        """Inicia los threads de workers si no están corriendo."""
        if any(t.is_alive() for t in self.threads):
            log.warning(f"[{self.session_id[:8]}] Workers ya están corriendo.")
            return

        self.stop_event.clear()
        self.pause_event.set()
        self.threads = []

        for target in targets:
            t = threading.Thread(target=target, args=(self.session_id,), daemon=True)
            self.threads.append(t)
            t.start()
        
        log.info(f"[{self.session_id[:8]}] Iniciados {len(self.threads)} workers.")

    def stop_workers(self):
        """Señala parada y espera a los threads (Chrome cierra)."""
        log.info(f"[{self.session_id[:8]}] Deteniendo workers...")
        self.stop_event.set()
        self.pause_event.set()  # Ensure they are not stuck in pause
        
        for t in self.threads:
            if t.is_alive():
                t.join(timeout=15)  # Dar tiempo a Chrome para cerrar
        self.threads = []
        log.info(f"[{self.session_id[:8]}] Workers detenidos y Chrome cerrado.")

    def pause_workers(self):
        log.info(f"[{self.session_id[:8]}] Pausando workers...")
        self.pause_event.clear()

    def resume_workers(self):
        log.info(f"[{self.session_id[:8]}] Reanudando workers...")
        self.pause_event.set()

    def is_running(self) -> bool:
        return any(t.is_alive() for t in self.threads)

    def is_paused(self) -> bool:
        return not self.pause_event.is_set()

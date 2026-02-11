
import threading
import time
import logging
from typing import List

log = logging.getLogger("ORCHESTRATOR")

class Orchestrator:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Orchestrator, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self._initialized = True
        
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()  # Start unpaused (set = running)
        
        self.threads: List[threading.Thread] = []

    def start_workers(self, targets: List[callable]):
        """Inicia los threads de workers si no están corriendo."""
        if any(t.is_alive() for t in self.threads):
            log.warning("Workers ya están corriendo.")
            return

        self.stop_event.clear()
        self.pause_event.set()
        self.threads = []

        for target in targets:
            t = threading.Thread(target=target, daemon=True)
            self.threads.append(t)
            t.start()
        
        log.info(f"Iniciados {len(self.threads)} workers.")

    def stop_workers(self):
        """Señala parada y espera a los threads."""
        log.info("Deteniendo workers...")
        self.stop_event.set()
        self.pause_event.set() # Ensure they are not stuck in pause
        
        for t in self.threads:
            if t.is_alive():
                t.join(timeout=5)
        self.threads = []
        log.info("Workers detenidos.")

    def pause_workers(self):
        log.info("Pausando workers...")
        self.pause_event.clear()

    def resume_workers(self):
        log.info("Reanudando workers...")
        self.pause_event.set()

    def is_running(self) -> bool:
        return any(t.is_alive() for t in self.threads)

    def is_paused(self) -> bool:
        return not self.pause_event.is_set()

# Singleton global
orchestrator = Orchestrator()

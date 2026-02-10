"""
Orquestador de Workers.

Gestiona los hilos de los workers de Sunedu y Minedu,
con capacidad de start/stop/restart y monitoreo de salud.
"""
import threading
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any

from workers import sunedu_worker_loop, minedu_worker_loop

log = logging.getLogger("ORCHESTRATOR")


class WorkerInfo:
    """Información de estado de un worker."""

    def __init__(self, name: str):
        self.name = name
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        self.restart_count = 0

    @property
    def is_running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "running": self.is_running,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "restart_count": self.restart_count,
            "thread_id": self.thread.ident if self.thread else None,
        }


class Orchestrator:
    """
    Orquestador singleton que gestiona los workers de Sunedu y Minedu.
    Cada worker corre en su propio hilo daemon con su instancia de Chrome.
    """

    _instance: Optional["Orchestrator"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.workers: Dict[str, WorkerInfo] = {
            "sunedu": WorkerInfo("sunedu"),
            "minedu": WorkerInfo("minedu"),
        }
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_stop = threading.Event()
        log.info("[ORCHESTRATOR] Inicializado")

    # ── Iniciar un worker específico ──
    def start_worker(self, name: str) -> bool:
        """Inicia un worker por nombre ('sunedu' o 'minedu')."""
        if name not in self.workers:
            log.error(f"[ORCHESTRATOR] Worker desconocido: {name}")
            return False

        info = self.workers[name]
        if info.is_running:
            log.warning(f"[ORCHESTRATOR] {name} ya está corriendo")
            return True

        # Reset del stop event
        info.stop_event.clear()

        # Seleccionar función del worker
        target_fn = sunedu_worker_loop if name == "sunedu" else minedu_worker_loop

        # Crear y arrancar hilo
        info.thread = threading.Thread(
            target=target_fn,
            args=(info.stop_event,),
            name=f"worker-{name}",
            daemon=True,
        )
        info.started_at = datetime.utcnow()
        info.stopped_at = None
        info.thread.start()

        log.info(f"[ORCHESTRATOR] Worker {name} iniciado (thread={info.thread.ident})")
        return True

    # ── Detener un worker específico ──
    def stop_worker(self, name: str, timeout: float = 30) -> bool:
        """Detiene un worker de forma graceful."""
        if name not in self.workers:
            return False

        info = self.workers[name]
        if not info.is_running:
            log.info(f"[ORCHESTRATOR] {name} ya está detenido")
            return True

        log.info(f"[ORCHESTRATOR] Deteniendo {name}...")
        info.stop_event.set()

        # Esperar a que el hilo termine
        if info.thread:
            info.thread.join(timeout=timeout)
            if info.thread.is_alive():
                log.warning(f"[ORCHESTRATOR] {name} no respondió en {timeout}s (forzando)")
            else:
                log.info(f"[ORCHESTRATOR] {name} detenido correctamente")

        info.stopped_at = datetime.utcnow()
        return True

    # ── Iniciar todos ──
    def start_all(self) -> Dict[str, bool]:
        """Inicia ambos workers."""
        results = {}
        for name in self.workers:
            results[name] = self.start_worker(name)
        self._start_monitor()
        return results

    # ── Detener todos ──
    def stop_all(self, timeout: float = 30) -> Dict[str, bool]:
        """Detiene ambos workers."""
        self._stop_monitor()
        results = {}
        for name in self.workers:
            results[name] = self.stop_worker(name, timeout)
        return results

    # ── Estado ──
    def status(self) -> Dict[str, Any]:
        """Retorna el estado de todos los workers."""
        return {
            name: info.to_dict()
            for name, info in self.workers.items()
        }

    # ── Monitor de salud ──
    def _start_monitor(self):
        """Inicia el hilo monitor que reinicia workers caídos."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return

        self._monitor_stop.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="worker-monitor",
            daemon=True,
        )
        self._monitor_thread.start()
        log.info("[ORCHESTRATOR] Monitor de salud iniciado")

    def _stop_monitor(self):
        self._monitor_stop.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

    def _monitor_loop(self):
        """Revisa cada 15s si algún worker murió inesperadamente y lo reinicia."""
        while not self._monitor_stop.is_set():
            for name, info in self.workers.items():
                # Si se solicitó stop, no reiniciar
                if info.stop_event.is_set():
                    continue

                # Si el hilo murió pero no se pidió stop → reiniciar
                if info.thread is not None and not info.thread.is_alive():
                    log.warning(f"[MONITOR] Worker {name} murió inesperadamente. Reiniciando...")
                    info.restart_count += 1
                    self.start_worker(name)

            self._monitor_stop.wait(timeout=15)

        log.info("[ORCHESTRATOR] Monitor detenido")

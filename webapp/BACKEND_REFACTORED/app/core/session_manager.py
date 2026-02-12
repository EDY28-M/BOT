"""
SessionManager — Gestiona orchestrators por sesión.
Cada sesión (browser tab) tiene su propio par de workers.
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from app.core.config import MAX_GLOBAL_WORKERS, SESSION_IDLE_TIMEOUT

log = logging.getLogger("SESSION_MANAGER")


class SessionInfo:
    """Datos de una sesión activa."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.orchestrator = None  # Se asigna al hacer start
        self.last_activity = datetime.utcnow()
        self.worker_count = 0  # Cuántos Chrome instances usa esta sesión

    def touch(self):
        self.last_activity = datetime.utcnow()

    def is_idle(self) -> bool:
        return (datetime.utcnow() - self.last_activity).total_seconds() > SESSION_IDLE_TIMEOUT


class SessionManager:
    """Singleton que gestiona todas las sesiones activas."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._sessions: Dict[str, SessionInfo] = {}
        self._global_lock = threading.Lock()
        self._total_workers = 0

    def touch(self, session_id: str):
        """Registra actividad de la sesión."""
        with self._global_lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionInfo(session_id)
            self._sessions[session_id].touch()

    def get_session(self, session_id: str) -> SessionInfo:
        """Obtiene o crea info de sesión."""
        with self._global_lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionInfo(session_id)
            self._sessions[session_id].touch()
            return self._sessions[session_id]

    def can_start_workers(self, num_workers: int = 2) -> bool:
        """Verifica si hay capacidad global para más workers."""
        with self._global_lock:
            return (self._total_workers + num_workers) <= MAX_GLOBAL_WORKERS

    def register_workers(self, session_id: str, count: int = 2):
        """Registra que la sesión inició N workers."""
        with self._global_lock:
            info = self._sessions.get(session_id)
            if info:
                info.worker_count = count
                self._total_workers += count
                log.info(f"[SESSION {session_id[:8]}] +{count} workers (global: {self._total_workers}/{MAX_GLOBAL_WORKERS})")

    def unregister_workers(self, session_id: str):
        """Libera los workers de una sesión."""
        with self._global_lock:
            info = self._sessions.get(session_id)
            if info and info.worker_count > 0:
                self._total_workers -= info.worker_count
                self._total_workers = max(0, self._total_workers)
                log.info(f"[SESSION {session_id[:8]}] -{info.worker_count} workers (global: {self._total_workers}/{MAX_GLOBAL_WORKERS})")
                info.worker_count = 0

    def get_orchestrator(self, session_id: str):
        """Obtiene el orchestrator de una sesión (puede ser None)."""
        info = self._sessions.get(session_id)
        return info.orchestrator if info else None

    def set_orchestrator(self, session_id: str, orchestrator):
        """Asigna un orchestrator a la sesión."""
        with self._global_lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionInfo(session_id)
            self._sessions[session_id].orchestrator = orchestrator

    def session_has_running_workers(self, session_id: str) -> bool:
        """Verifica si la sesión tiene workers corriendo."""
        info = self._sessions.get(session_id)
        if info and info.orchestrator:
            return info.orchestrator.is_running()
        return False

    def cleanup_idle_sessions(self):
        """Limpia sesiones inactivas (llamar periódicamente)."""
        with self._global_lock:
            idle_sessions = [
                sid for sid, info in self._sessions.items()
                if info.is_idle() and not (info.orchestrator and info.orchestrator.is_running())
            ]

        for sid in idle_sessions:
            info = self._sessions.get(sid)
            if info:
                if info.orchestrator and info.orchestrator.is_running():
                    info.orchestrator.stop_workers()
                    self._total_workers -= info.worker_count
                    self._total_workers = max(0, self._total_workers)
                log.info(f"[CLEANUP] Sesión {sid[:8]} eliminada (idle {SESSION_IDLE_TIMEOUT}s)")
                with self._global_lock:
                    del self._sessions[sid]

        return len(idle_sessions)

    def get_stats(self) -> dict:
        """Estadísticas globales."""
        with self._global_lock:
            active = sum(1 for i in self._sessions.values() if i.orchestrator and i.orchestrator.is_running())
            return {
                "total_sessions": len(self._sessions),
                "active_sessions": active,
                "total_workers": self._total_workers,
                "max_workers": MAX_GLOBAL_WORKERS,
            }

    def get_all_session_ids(self) -> list:
        """Retorna todos los session_ids activos."""
        with self._global_lock:
            return list(self._sessions.keys())


# Singleton global
session_manager = SessionManager()

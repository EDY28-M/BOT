"""
FastAPI dependencies — inyección de session_id.
"""

from fastapi import Request, HTTPException
from app.core.session_manager import session_manager


def get_session_id(request: Request) -> str:
    """
    Extrae X-Session-ID del header.
    Si no viene, retorna 400.
    También registra actividad de la sesión.
    """
    session_id = request.headers.get("X-Session-ID")
    if not session_id or len(session_id) < 8:
        raise HTTPException(
            status_code=400,
            detail="Header X-Session-ID es requerido. Cada navegador debe enviar un UUID único."
        )
    
    # Registrar actividad
    session_manager.touch(session_id)
    return session_id

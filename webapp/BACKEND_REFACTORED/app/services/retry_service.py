
from app.db.repository import DniRepository

class RetryService:
    def __init__(self):
        self.repo = DniRepository()

    def retry_failed(self, session_id: str) -> int:
        """
        Re-encola registros con estado ERROR_* o NOT_FOUND de esta sesión.
        Retorna la cantidad de registros reencolados.
        """
        result = self.repo.reintentar_no_encontrados(session_id)
        return result.get("reencolados", 0)

    def recover_stuck(self, session_id: str) -> dict:
        """
        Recupera registros que se quedaron en estado PROCESANDO_*
        (por ejemplo, si se cayó el worker) de esta sesión.
        """
        return self.repo.recuperar_procesando(session_id)

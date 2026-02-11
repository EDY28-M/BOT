
from app.db.repository import DniRepository

class RetryService:
    def __init__(self):
        self.repo = DniRepository()

    def retry_failed(self) -> int:
        """
        Re-encola registros con estado ERROR_* o NOT_FOUND.
        Retorna la cantidad de registros reencolados.
        """
        result = self.repo.reintentar_no_encontrados()
        return result.get("reencolados", 0)

    def recover_stuck(self) -> dict:
        """
        Recupera registros que se quedaron en estado PROCESANDO_* 
        (por ejemplo, si se cayó el worker).
        """
        return self.repo.recuperar_procesando()

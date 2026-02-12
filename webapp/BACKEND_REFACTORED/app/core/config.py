
"""
Configuración centralizada del sistema.
"""
import os
from pathlib import Path

# --- Rutas ---
# Base dir is app/.. (i.e. BACKEND_REFACTORED)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_DIR = BASE_DIR / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "registros.db"

DATABASE_URL = f"sqlite:///{DB_PATH}"

# --- URLs de consulta ---
SUNEDU_URL = "https://constanciasweb.sunedu.gob.pe/#/modulos/grados-y-titulos"
MINEDU_URL = "https://titulosinstitutos.minedu.gob.pe/"

# --- Estados del pipeline ---
class Estado:
    PENDIENTE          = "PENDIENTE"
    PROCESANDO_SUNEDU  = "PROCESANDO_SUNEDU"
    FOUND_SUNEDU       = "FOUND_SUNEDU"
    CHECK_MINEDU       = "CHECK_MINEDU"
    PROCESANDO_MINEDU  = "PROCESANDO_MINEDU"
    FOUND_MINEDU       = "FOUND_MINEDU"
    NOT_FOUND          = "NOT_FOUND"
    ERROR_SUNEDU       = "ERROR_SUNEDU"
    ERROR_MINEDU       = "ERROR_MINEDU"

    TERMINALES = {FOUND_SUNEDU, FOUND_MINEDU, NOT_FOUND, ERROR_SUNEDU, ERROR_MINEDU}

# --- Workers ---
# Tiempos de espera para simular comportamiento humano
SUNEDU_SLEEP_MIN = 3.0
SUNEDU_SLEEP_MAX = 4.2
SUNEDU_SLEEP_NOT_FOUND = 3.6
MINEDU_SLEEP_MIN = 1.0
MINEDU_SLEEP_MAX = 2.0
WORKER_POLL_INTERVAL = 2
SUNEDU_MAX_RETRIES = 5
MINEDU_MAX_RETRIES = 8
RETRY_EXTRA_SLEEP  = 1.2

# --- Navegador (Botasaurus) ---
HEADLESS = os.getenv("HEADLESS", "False").lower() == "true"
BLOCK_IMAGES_SUNEDU = True
BLOCK_IMAGES_MINEDU = False
WINDOW_SIZE = (1366, 768)

# --- API ---
API_HOST = os.getenv("HOST", "0.0.0.0")
API_PORT = int(os.getenv("PORT", 8000))

# --- Sesiones ---
MAX_GLOBAL_WORKERS = 10          # Máx Chrome instances en total (todas las sesiones)
SESSION_IDLE_TIMEOUT = 1800      # Segundos antes de limpiar sesión inactiva (30 min)

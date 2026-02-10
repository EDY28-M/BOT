"""
Configuración centralizada del sistema de validación de grados académicos.
"""
from pathlib import Path

# --- Rutas ---
BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = BASE_DIR / "data" / "registros.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

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
SUNEDU_SLEEP_MIN = 3.0
SUNEDU_SLEEP_MAX = 4.2
SUNEDU_SLEEP_NOT_FOUND = 3.6
MINEDU_SLEEP_MIN = 1.0
MINEDU_SLEEP_MAX = 2.0
WORKER_POLL_INTERVAL = 2
SUNEDU_MAX_RETRIES = 5
MINEDU_MAX_RETRIES = 8
RETRY_EXTRA_SLEEP  = 1.2

# --- Navegador ---
HEADLESS = False
BLOCK_IMAGES_SUNEDU = True
BLOCK_IMAGES_MINEDU = False

# --- API / Streamlit ---
API_HOST = "127.0.0.1"
API_PORT = 8000
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"
STREAMLIT_PORT = 8501

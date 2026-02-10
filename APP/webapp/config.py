"""
Configuración centralizada del sistema de validación de grados académicos.
"""
from pathlib import Path

# ─── Rutas ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = BASE_DIR / "data" / "registros.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

# ─── URLs de consulta ─────────────────────────────────────────────────
SUNEDU_URL = "https://constanciasweb.sunedu.gob.pe/#/modulos/grados-y-titulos"
MINEDU_URL = "https://titulosinstitutos.minedu.gob.pe/"

# ─── Estados del pipeline ─────────────────────────────────────────────
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

# ─── Workers ──────────────────────────────────────────────────────────
SUNEDU_SLEEP_MIN = 3       # Segundos mínimos entre consultas Sunedu
SUNEDU_SLEEP_MAX = 5       # Segundos máximos entre consultas Sunedu
MINEDU_SLEEP_MIN = 2       # Segundos mínimos entre consultas Minedu
MINEDU_SLEEP_MAX = 4       # Segundos máximos entre consultas Minedu
WORKER_POLL_INTERVAL = 5   # Segundos de espera cuando no hay trabajo
SUNEDU_MAX_RETRIES = 5     # Reintentos por DNI en Sunedu
MINEDU_MAX_RETRIES = 8     # Reintentos por DNI en Minedu

# ─── Navegador ────────────────────────────────────────────────────────
HEADLESS = False            # Mostrar navegador (False) o en background (True)
BLOCK_IMAGES_SUNEDU = True  # Bloquear imágenes en Sunedu (más rápido)
BLOCK_IMAGES_MINEDU = False # Minedu necesita imágenes para el captcha

# ─── API / Streamlit ──────────────────────────────────────────────────
API_HOST = "127.0.0.1"
API_PORT = 8000
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"
STREAMLIT_PORT = 8501

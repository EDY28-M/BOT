
import logging
import sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(name)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    # Silenciar logs ruidosos de librerías externas si es necesario
    logging.getLogger("urllib3").setLevel(logging.WARNING)

log = logging.getLogger("APP")

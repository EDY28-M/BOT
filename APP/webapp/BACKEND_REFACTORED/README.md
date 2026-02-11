
# Validacion de Grados y Titulos (Backend Refactorizado)

Este proyecto ha sido refactorizado para seguir una arquitectura modular y escalable, separando la lógica de scraping, base de datos y API.

## Estructura

- `app/core`: Configuración y logging.
- `app/db`: Modelos y repositorio de base de datos (SQLite).
- `app/scrapers`: Lógica de extracción (Sunedu con Botasaurus, Minedu con OCR).
- `app/workers`: Orquestación de procesos en segundo plano.
- `app/api`: Endpoints FastAPI.

## Requisitos

- Python 3.10+
- Chrome instalado (para Botasaurus)

## Instalación

1.  Crear entorno virtual (opcional pero recomendado):
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

2.  Instalar dependencias:
    ```bash
    pip install -r requirements.txt
    ```

3.  Instalar navegadores de Botasaurus (si es necesario):
    ```bash
    python -m botasaurus install
    ```

## Ejecución

Para iniciar el servidor API y el sistema de workers:

```bash
python main.py
```

El servidor iniciará en `http://127.0.0.1:8000`.
La documentación interactiva de la API está en `http://127.0.0.1:8000/docs`.

## Funcionalidad

- **Upload**: Sube archivos Excel/CSV con DNIs en `/api/upload`.
- **Workers**: Se inician automáticamente al subir o manualmente vía `/api/workers/start`.
- **Sunedu**: Usa `Botasaurus` para evasión de detección.
- **Minedu**: Usa `ddddocr` para resolver captchas.
- **Resultados**: Descarga en Excel vía `/api/resultados`.

## Notas de Desarrollo

- La base de datos es SQLite (`data/registros.db`) configurada con WAL mode para concurrencia.
- Los logs se muestran en consola.

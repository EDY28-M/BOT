# 🎓 Validador de Grados Académicos — Web App

Pipeline automático de validación masiva de grados y títulos por DNI.

## 🆕 Nuevo: Dashboard Elite v2.0

Disponible ahora con interfaz **Brutal SaaS Dark Mode**:
- 🎨 **Glassmorphism** y animaciones fluidas
- 📊 **Métricas en vivo** con auto-refresh (2s)
- 🖥️ **Consola de logs** estilo terminal hacker
- 🔄 **Pipeline Waterfall** visual

```bash
# Iniciar el nuevo dashboard elite
iniciar_dashboard_elite.bat
# o: iniciar_sistema_completo.bat (API + Dashboard)
```

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                     │
│  ┌─────────────────┐    ┌─────────────────┐                        │
│  │  Dashboard      │    │  Dashboard      │                        │
│  │  Clásico        │    │  Elite (Nuevo)  │                        │
│  │  (app.py)       │    │  (app_ui.py)    │                        │
│  │  Puerto 8501    │    │  Puerto 8502    │                        │
│  └────────┬────────┘    └────────┬────────┘                        │
└───────────┼──────────────────────┼──────────────────────────────────┘
            │                      │
            └──────────────────────┘
                       │
                       ▼ HTTP/REST
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    FastAPI (api.py)                          │    │
│  │                    Puerto 8000                               │    │
│  └─────────────────────────┬───────────────────────────────────┘    │
│                            │                                        │
│                   ┌────────┴────────┐                               │
│                   │  Orchestrator   │                               │
│                   │  (Hilos daemon) │                               │
│                   └────────┬────────┘                               │
│          ┌─────────────────┼─────────────────┐                      │
│          ▼                 ▼                 ▼                      │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│  │Worker SUNEDU  │  │Worker MINEDU  │  │   SQLite      │           │
│  │(Botasaurus)   │  │(Botasaurus +  │  │   (WAL mode)  │           │
│  │Universidades  │  │ddddocr OCR)   │  │   registros.db│           │
│  └───────────────┘  └───────────────┘  └───────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

## Pipeline de Estados (Cascada Condicional)

```
                    ┌─────────────────┐
         ┌─────────│  FOUND_SUNEDU   │────────┐
         │         │      ✅         │        │
         │         └─────────────────┘        │
         │                                    │
┌────────▼────────┐                  ┌────────▼────────┐
│  PENDIENTE      │                  │  FOUND_MINEDU   │
│                 │──────────────────│      ✅         │
└────────┬────────┘   No encontrado   └─────────────────┘
         │         en SUNEDU
         │
┌────────▼────────┐         ┌─────────────────┐
│PROCESANDO_SUNEDU│─────────│   NOT_FOUND     │
│                 │         │      🚫         │
└─────────────────┘         └─────────────────┘
                                    ▲
                                    │
                           ┌────────┴────────┐
                           │PROCESANDO_MINEDU│
                           └─────────────────┘
```

## Instalación

```bash
cd webapp
pip install -r requirements.txt
```

## 🚀 Ejecución

### Opción 1: Dashboard Elite (Recomendado)
```bash
# Primero la API
iniciar_api.bat

# Luego el Dashboard Elite en otra terminal
iniciar_dashboard_elite.bat
```

### Opción 2: Todo junto (automático)
```bash
iniciar_sistema_completo.bat
```

### Opción 3: Componentes individuales
```bash
# Terminal 1 — API Server
iniciar_api.bat
# o: python api.py

# Terminal 2 — Dashboard Clásico
iniciar_dashboard.bat
# o: streamlit run app.py --server.port 8501

# Terminal 3 — Dashboard Elite
streamlit run frontwebapp/app_ui.py --server.port 8502
```

## 🎨 Dashboard Elite - Características

| Característica | Descripción |
|----------------|-------------|
| **Dark Mode** | Tema oscuro cyberpunk con gradientes |
| **Glassmorphism** | Efecto cristal en contenedores |
| **Auto-refresh** | Actualización automática cada 2 segundos |
| **Métricas Vivas** | 4 KPIs principales con colores diferenciados |
| **Pipeline Waterfall** | Barras de progreso animadas por worker |
| **Terminal Hacker** | Consola de logs con scroll en tiempo real |
| **Tablas Interactivas** | Datos con filtros y ordenamiento |

## URLs de Acceso

| Servicio | URL | Descripción |
|----------|-----|-------------|
| API Docs | http://localhost:8000/docs | Documentación Swagger |
| API | http://localhost:8000 | Endpoints REST |
| Dashboard Clásico | http://localhost:8501 | Interfaz básica Streamlit |
| **Dashboard Elite** | **http://localhost:8502** | **🌟 Nueva interfaz SaaS** |

## Uso

1. **Inicia el sistema**: `iniciar_sistema_completo.bat`
2. **Abre el Dashboard Elite**: http://localhost:8502
3. **Sube un archivo Excel/CSV** con columna `DNI` o `DOCUMENTO`
4. **Haz clic en INICIAR** para arrancar los workers
5. **Observa el progreso** en tiempo real (métricas + terminal)
6. **Descarga resultados** en Excel cuando termine

## API REST

Documentación interactiva: http://127.0.0.1:8000/docs

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/upload` | POST | Subir Excel/CSV con DNIs |
| `/api/status` | GET | Conteos por estado del pipeline |
| `/api/lotes` | GET | Listar lotes subidos |
| `/api/registros` | GET | Listar registros (con filtros) |
| `/api/resultados` | GET | Descargar Excel con resultados |
| `/api/workers/start` | POST | Iniciar workers |
| `/api/workers/stop` | POST | Detener workers |
| `/api/workers/status` | GET | Estado de los workers |

## Estructura de Archivos

```
webapp/
├── config.py                    # Configuración centralizada
├── database.py                  # Modelos SQLAlchemy + CRUD
├── workers.py                   # Lógica de scraping (SUNEDU/MINEDU)
├── orchestrator.py              # Gestión de hilos de workers
├── api.py                       # FastAPI (endpoints REST)
├── app.py                       # Dashboard Streamlit CLÁSICO
├── requirements.txt             # Dependencias Python
│
├── frontwebapp/                 # 🆕 NUEVO: Frontend Elite
│   ├── __init__.py
│   ├── app_ui.py               # Dashboard SaaS Dark Mode
│   └── README.md               # Documentación del frontend
│
├── iniciar_api.bat             # Iniciar solo la API
├── iniciar_dashboard.bat       # Iniciar dashboard CLÁSICO
├── iniciar_dashboard_elite.bat # 🆕 Iniciar dashboard ELITE
├── iniciar_sistema_completo.bat # 🆕 Iniciar TODO (API + Elite)
├── iniciar_todo.bat            # Iniciar API + Dashboard clásico
│
└── data/
    └── registros.db            # Base de datos SQLite (auto-creada)
```

## Estados del Pipeline

| Estado | Color | Significado |
|--------|-------|-------------|
| `PENDIENTE` | 🟡 Amarillo | Esperando procesamiento |
| `PROCESANDO_SUNEDU` | 🔵 Cyan | Scraping en SUNEDU |
| `FOUND_SUNEDU` | 🟢 Verde | Encontrado en SUNEDU (universidad) |
| `CHECK_MINEDU` | 🟠 Naranja | Pendiente de verificar en MINEDU |
| `PROCESANDO_MINEDU` | 🔵 Azul | Scraping en MINEDU |
| `FOUND_MINEDU` | 🟢 Verde | Encontrado en MINEDU (instituto) |
| `NOT_FOUND` | 🔴 Rojo | No se encontró título |
| `ERROR_SUNEDU` | 🔴 Rojo | Error en worker SUNEDU |
| `ERROR_MINEDU` | 🔴 Rojo | Error en worker MINEDU |

## Configuración

Editar `config.py` para ajustar:

```python
# Tiempos de espera anti-ban
SUNEDU_SLEEP_MIN = 3
SUNEDU_SLEEP_MAX = 5

# Reintentos
SUNEDU_MAX_RETRIES = 5
MINEDU_MAX_RETRIES = 8

# Modo headless del navegador
HEADLESS = False  # True = sin ventana

# Puertos
API_PORT = 8000
STREAMLIT_PORT = 8501  # Dashboard clásico
```

## Troubleshooting

### Error: "No se puede conectar con la API"
- Verifica que la API esté corriendo: `python api.py`
- Comprueba el puerto en `config.py` y `app_ui.py`

### Los workers no inician
- Verifica que tengas Chrome instalado
- Comprueba la instalación de Botasaurus: `pip install botasaurus`

### Error en MINEDU (captcha)
- Verifica que ddddocr esté instalado: `pip install ddddocr`
- MINEDU requiere imágenes activadas (`BLOCK_IMAGES_MINEDU = False`)

## Licencia

Proyecto privado - Uso interno.

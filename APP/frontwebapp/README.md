# 🚀 Dashboard ETL Elite - Frontend

Interfaz gráfica brutal para el Validador de Grados Académicos.

## 🎨 Características

### Diseño Visual
- **Dark Mode Cyberpunk** con gradientes dinámicos
- **Glassmorphism** en todos los contenedores
- **Tipografía moderna**: JetBrains Mono + Inter
- **Animaciones CSS fluidas** (hover, pulse, glow)

### Funcionalidad
- **Métricas en vivo**: 4 KPIs principales con auto-refresh (2s)
- **Pipeline Waterfall**: Barras de progreso por worker (SUNEDU/MINEDU)
- **Consola de logs**: Terminal estilo hacker con scroll
- **Visualización de datos**: Tablas interactivas con filtros
- **Descarga de resultados**: Exportación a Excel

## 🚀 Uso

### Opción 1: Script Batch (Recomendado)
```bash
# Desde la carpeta webapp
iniciar_dashboard_elite.bat
```

### Opción 2: Comando manual
```bash
cd webapp
python -m streamlit run frontwebapp/app_ui.py --server.port=8502
```

## 🔌 Conexión con Backend

El dashboard se conecta automáticamente a la API en `http://127.0.0.1:8000`.

**⚠️ Importante**: Asegúrate de iniciar la API primero:
```bash
iniciar_api.bat
```

## 📁 Estructura

```
frontwebapp/
├── __init__.py      # Inicialización del módulo
├── app_ui.py        # Código principal del dashboard
└── README.md        # Esta documentación
```

## 🎛️ Controles

| Elemento | Descripción |
|----------|-------------|
| **▶ INICIAR** | Inicia los workers de scraping |
| **⏹ DETENER** | Detiene los workers |
| **📤 Subir DNIs** | Carga archivo Excel/CSV con DNIs |
| **🔄 Auto-refresh** | Activa/desactiva actualización automática |
| **📥 Descargar Excel** | Exporta resultados completos |

## 🌈 Estados del Pipeline

```
PENDIENTE → PROCESANDO_SUNEDU → FOUND_SUNEDU
                                    ↓
                            CHECK_MINEDU → PROCESANDO_MINEDU → FOUND_MINEDU
                                                                    ↓
                                                              NOT_FOUND
```

## 🔧 Personalización

Para cambiar el puerto del dashboard, edita `iniciar_dashboard_elite.bat`:
```bash
--server.port=8502  # Cambia 8502 por tu puerto preferido
```

Para cambiar la URL de la API, edita `app_ui.py`:
```python
API_BASE_URL = "http://127.0.0.1:8000"  # Modifica esta línea
```

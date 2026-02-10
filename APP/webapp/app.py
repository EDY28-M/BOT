"""
Dashboard Streamlit — Validador de Grados Académicos.

Interfaz web para:
  • Subir archivos Excel/CSV con DNIs
  • Ver progreso en tiempo real (barras + métricas)
  • Controlar workers (iniciar / detener)
  • Descargar reporte unificado
"""
import io
import time
import requests
import pandas as pd
import streamlit as st

from config import API_BASE_URL

# ═══════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN DE PÁGINA
# ═══════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Validador de Grados Académicos",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

API = API_BASE_URL


def api_get(path: str):
    """GET request a la API."""
    try:
        r = requests.get(f"{API}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.ConnectionError:
        return None
    except Exception as e:
        st.error(f"Error API: {e}")
        return None


def api_post(path: str, **kwargs):
    """POST request a la API."""
    try:
        r = requests.post(f"{API}{path}", timeout=30, **kwargs)
        r.raise_for_status()
        return r.json()
    except requests.ConnectionError:
        return None
    except Exception as e:
        st.error(f"Error API: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════════════

st.title("🎓 Validador de Grados Académicos")
st.caption("Pipeline automático: SUNEDU → MINEDU | Consulta masiva por DNI")

# Verificar conexión con API
api_status = api_get("/api/status")
if api_status is None:
    st.error(
        f"⚠️ No se puede conectar con la API en **{API}**. "
        "Asegúrate de que el servidor esté corriendo (`iniciar_api.bat`)."
    )
    st.stop()


# ═══════════════════════════════════════════════════════════════════════
#  SIDEBAR — Control de Workers y Upload
# ═══════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("⚙️ Control del Sistema")

    # ── Estado de Workers ──
    st.subheader("Workers")
    workers = api_get("/api/workers/status")

    if workers:
        col1, col2 = st.columns(2)
        for name, col in [("sunedu", col1), ("minedu", col2)]:
            w = workers.get(name, {})
            running = w.get("running", False)
            with col:
                status_icon = "🟢" if running else "🔴"
                st.markdown(f"**{status_icon} {name.upper()}**")
                if running and w.get("started_at"):
                    st.caption(f"Desde: {w['started_at'][:19]}")
                if w.get("restart_count", 0) > 0:
                    st.caption(f"Reinicios: {w['restart_count']}")

    st.divider()

    # Botones de control
    col_start, col_stop = st.columns(2)
    with col_start:
        if st.button("▶ Iniciar", use_container_width=True, type="primary"):
            result = api_post("/api/workers/start")
            if result:
                st.success("Workers iniciados")
                time.sleep(1)
                st.rerun()
    with col_stop:
        if st.button("⏹ Detener", use_container_width=True):
            result = api_post("/api/workers/stop")
            if result:
                st.warning("Workers detenidos")
                time.sleep(1)
                st.rerun()

    st.divider()

    # ── Upload de archivo ──
    st.subheader("📤 Subir DNIs")
    uploaded = st.file_uploader(
        "Archivo Excel o CSV con columna 'DNI'",
        type=["xlsx", "xls", "csv"],
        help="El archivo debe tener una columna llamada 'DNI' o 'DOCUMENTO'",
    )

    if uploaded is not None:
        if st.button("🚀 Cargar DNIs", use_container_width=True, type="primary"):
            with st.spinner("Subiendo archivo..."):
                try:
                    files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
                    r = requests.post(f"{API}/api/upload", files=files, timeout=60)
                    r.raise_for_status()
                    data = r.json()
                    st.success(
                        f"✅ Lote **#{data['lote_id']}** creado — "
                        f"**{data['total_dnis']}** DNIs cargados"
                    )
                    time.sleep(1)
                    st.rerun()
                except requests.HTTPError as e:
                    body = e.response.json() if e.response else {}
                    st.error(f"Error: {body.get('detail', str(e))}")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()

    # ── Auto-refresh ──
    auto_refresh = st.checkbox("🔄 Auto-actualizar (5s)", value=False)
    if st.button("🔄 Actualizar ahora", use_container_width=True):
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════
#  PANEL PRINCIPAL — Métricas y Progreso
# ═══════════════════════════════════════════════════════════════════════

status = api_get("/api/status")
if not status:
    st.info("Sin datos de estado disponibles.")
    st.stop()

total = status.get("total", 0)
terminados = status.get("terminados", 0)
progreso = status.get("progreso_pct", 0)
pipeline = status.get("pipeline", {})

# ── Métricas principales ──
st.subheader("📊 Resumen General")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total DNIs", total)
m2.metric("Completados", terminados)
m3.metric("En proceso", status.get("en_proceso", 0))
m4.metric("Progreso", f"{progreso}%")

# Barra de progreso general
if total > 0:
    st.progress(min(progreso / 100, 1.0), text=f"Progreso general: {terminados}/{total}")

st.divider()

# ── Pipeline detallado ──
col_sunedu, col_minedu = st.columns(2)

with col_sunedu:
    st.subheader("🏛️ SUNEDU (Universidades)")
    s = pipeline.get("sunedu", {})
    s_total = s.get("pendientes", 0) + s.get("procesando", 0) + s.get("encontrados", 0) + s.get("errores", 0) + s.get("derivados_minedu", 0)
    s_done = s.get("encontrados", 0) + s.get("derivados_minedu", 0) + s.get("errores", 0)
    s_pct = (s_done / s_total * 100) if s_total > 0 else 0

    st.progress(min(s_pct / 100, 1.0), text=f"{s_done}/{s_total} ({s_pct:.0f}%)")

    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("⏳ Pendientes", s.get("pendientes", 0))
    sc2.metric("✅ Encontrados", s.get("encontrados", 0))
    sc3.metric("➡️ → Minedu", s.get("derivados_minedu", 0))

    if s.get("procesando", 0) > 0:
        st.info(f"🔄 Procesando: {s['procesando']}")
    if s.get("errores", 0) > 0:
        st.warning(f"❌ Errores: {s['errores']}")

with col_minedu:
    st.subheader("📚 MINEDU (Institutos)")
    m = pipeline.get("minedu", {})
    m_total = m.get("pendientes", 0) + m.get("procesando", 0) + m.get("encontrados", 0) + m.get("no_encontrados", 0) + m.get("errores", 0)
    m_done = m.get("encontrados", 0) + m.get("no_encontrados", 0) + m.get("errores", 0)
    m_pct = (m_done / m_total * 100) if m_total > 0 else 0

    st.progress(min(m_pct / 100, 1.0), text=f"{m_done}/{m_total} ({m_pct:.0f}%)" if m_total > 0 else "Sin DNIs derivados aún")

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("⏳ Pendientes", m.get("pendientes", 0))
    mc2.metric("✅ Encontrados", m.get("encontrados", 0))
    mc3.metric("🚫 No encontrados", m.get("no_encontrados", 0))

    if m.get("procesando", 0) > 0:
        st.info(f"🔄 Procesando: {m['procesando']}")
    if m.get("errores", 0) > 0:
        st.warning(f"❌ Errores: {m['errores']}")


# ═══════════════════════════════════════════════════════════════════════
#  TABLA DE RESULTADOS Y DESCARGA
# ═══════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("📋 Resultados")

# Filtros
tab_all, tab_sunedu, tab_minedu, tab_notfound, tab_errors = st.tabs(
    ["Todos", "SUNEDU ✅", "MINEDU ✅", "No encontrados", "Errores"]
)

filter_map = {
    "Todos": None,
    "SUNEDU ✅": "FOUND_SUNEDU",
    "MINEDU ✅": "FOUND_MINEDU",
    "No encontrados": "NOT_FOUND",
    "Errores": None,  # Manejado aparte
}


def mostrar_registros(estado_filtro=None, es_errores=False):
    """Muestra tabla de registros."""
    if es_errores:
        regs_s = api_get("/api/registros?estado=ERROR_SUNEDU&limit=1000") or []
        regs_m = api_get("/api/registros?estado=ERROR_MINEDU&limit=1000") or []
        registros = regs_s + regs_m
    elif estado_filtro:
        registros = api_get(f"/api/registros?estado={estado_filtro}&limit=1000") or []
    else:
        registros = api_get("/api/registros?limit=1000") or []

    if not registros:
        st.info("Sin registros para mostrar")
        return

    df = pd.DataFrame(registros)

    # Seleccionar columnas relevantes
    cols_mostrar = ["dni", "estado"]
    for c in ["sunedu_nombres", "sunedu_grado", "sunedu_institucion",
              "minedu_nombres", "minedu_titulo", "minedu_institucion",
              "error_msg", "updated_at"]:
        if c in df.columns:
            cols_mostrar.append(c)

    cols_presentes = [c for c in cols_mostrar if c in df.columns]
    st.dataframe(df[cols_presentes], use_container_width=True, hide_index=True)
    st.caption(f"Mostrando {len(df)} registros")


with tab_all:
    mostrar_registros()

with tab_sunedu:
    mostrar_registros("FOUND_SUNEDU")

with tab_minedu:
    mostrar_registros("FOUND_MINEDU")

with tab_notfound:
    mostrar_registros("NOT_FOUND")

with tab_errors:
    mostrar_registros(es_errores=True)

# ── Descarga ──
st.divider()
col_dl1, col_dl2 = st.columns([1, 3])
with col_dl1:
    if st.button("📥 Descargar Excel completo", type="primary", use_container_width=True):
        try:
            r = requests.get(f"{API}/api/resultados", timeout=60)
            r.raise_for_status()
            st.download_button(
                label="💾 Guardar archivo",
                data=r.content,
                file_name="resultados_validacion.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as e:
            st.error(f"Error descargando: {e}")


# ═══════════════════════════════════════════════════════════════════════
#  LOTES
# ═══════════════════════════════════════════════════════════════════════

st.divider()
with st.expander("📦 Lotes subidos"):
    lotes = api_get("/api/lotes")
    if lotes:
        df_lotes = pd.DataFrame(lotes)
        st.dataframe(df_lotes, use_container_width=True, hide_index=True)
    else:
        st.info("No hay lotes subidos")


# ═══════════════════════════════════════════════════════════════════════
#  DIAGRAMA DEL PIPELINE
# ═══════════════════════════════════════════════════════════════════════

with st.expander("🔀 Diagrama del Pipeline"):
    st.markdown("""
    ```
    ┌─────────────┐
    │  UPLOAD DNI  │
    │  (Excel/CSV) │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │  PENDIENTE   │  ← Estado inicial
    └──────┬──────┘
           │
           ▼
    ┌─────────────────┐     ┌──────────────────┐
    │  WORKER SUNEDU  │────▶│  FOUND_SUNEDU ✅  │  (Grado universitario)
    │  (Universidades)│     └──────────────────┘
    └──────┬──────────┘
           │ No encontrado
           ▼
    ┌─────────────────┐     ┌──────────────────┐
    │  WORKER MINEDU  │────▶│  FOUND_MINEDU ✅  │  (Título técnico)
    │  (Institutos)   │     └──────────────────┘
    └──────┬──────────┘
           │ No encontrado
           ▼
    ┌─────────────────┐
    │   NOT_FOUND 🚫   │
    └─────────────────┘
    ```
    """)


# ═══════════════════════════════════════════════════════════════════════
#  AUTO-REFRESH
# ═══════════════════════════════════════════════════════════════════════

if auto_refresh:
    time.sleep(5)
    st.rerun()

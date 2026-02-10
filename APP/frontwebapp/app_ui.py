"""
Validador de Grados Académicos — Dashboard v3.0
Pipeline ETL: SUNEDU → MINEDU
Diseño: Dark Cyberpunk · Glass Panels · Neon Accents
"""

import io
import time
import json
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any, List

# ─── Config ───────────────────────────────────────────────────────────
API_BASE_URL = "http://127.0.0.1:8000"
POLL_INTERVAL = 2

# ─── MEGA CSS ─────────────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
/* ═══ FONTS ═══ */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Fira+Code:wght@300;400;500&display=swap');
@import url('https://fonts.googleapis.com/icon?family=Material+Icons+Round');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

:root {
    --bg-dark: #0f0816;
    --bg-panel: rgba(25, 16, 34, 0.6);
    --primary: #a855f7;
    --primary-dim: rgba(168,85,247,0.12);
    --neon-green: #00ff9d;
    --neon-blue: #00f3ff;
    --neon-red: #ff0055;
    --border-color: rgba(168,85,247,0.2);
    --text-main: #e2e8f0;
    --text-dim: #94a3b8;
    --text-muted: #64748b;
}

/* ═══ STREAMLIT OVERRIDES ═══ */
#MainMenu, footer, header, .stDeployButton,
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

.block-container {
    padding: 1.5rem 2rem 1rem 2rem !important;
    max-width: 100% !important;
}

.stApp {
    background: var(--bg-dark) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    color: var(--text-main) !important;
}

/* ═══ BACKGROUND GLOW ═══ */
.stApp::before {
    content: '';
    position: fixed; top: -10%; right: -5%;
    width: 500px; height: 500px;
    background: rgba(168,85,247,0.08);
    border-radius: 50%; filter: blur(100px);
    pointer-events: none; z-index: 0;
}
.stApp::after {
    content: '';
    position: fixed; bottom: -10%; left: 10%;
    width: 400px; height: 400px;
    background: rgba(0,243,255,0.04);
    border-radius: 50%; filter: blur(80px);
    pointer-events: none; z-index: 0;
}

/* ═══ SIDEBAR ═══ */
section[data-testid="stSidebar"] {
    background: var(--bg-panel) !important;
    backdrop-filter: blur(12px) !important;
    border-right: 1px solid var(--border-color) !important;
    width: 320px !important;
}
section[data-testid="stSidebar"] * {
    font-family: 'Space Grotesk', sans-serif !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem !important;
}

/* ═══ GLASS PANEL ═══ */
.glass-panel {
    background: var(--bg-panel);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-color);
    border-radius: 0.75rem;
    padding: 1.25rem;
}

/* ═══ METRIC CARDS ═══ */
.metric-card {
    background: var(--bg-panel);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-color);
    border-radius: 0.75rem;
    padding: 1.25rem 1.5rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease;
}
.metric-card:hover { transform: translateY(-2px); }
.metric-card .mc-icon {
    position: absolute; right: 0; top: 0; padding: 1rem;
    opacity: 0.08; transition: opacity 0.2s;
}
.metric-card:hover .mc-icon { opacity: 0.18; }
.mc-label {
    font-size: 0.8rem; text-transform: uppercase;
    letter-spacing: 0.08em; color: var(--text-dim);
    font-weight: 500;
}
.mc-value {
    font-size: 2.5rem; font-weight: 700;
    color: #fff; line-height: 1.1; margin-top: 0.15rem;
    transition: transform 0.2s; transform-origin: left;
}
.metric-card:hover .mc-value { transform: scale(1.03); }
.mc-sub {
    font-size: 0.72rem; font-family: 'Fira Code', monospace;
    margin-top: 0.5rem; display: flex; align-items: center; gap: 4px;
}
.border-l-primary { border-left: 4px solid var(--primary) !important; }
.border-l-green   { border-left: 4px solid var(--neon-green) !important; }
.border-l-blue    { border-left: 4px solid var(--neon-blue) !important; }
.border-l-red     { border-left: 4px solid var(--neon-red) !important; }

/* ═══ PROGRESS BARS ═══ */
.pipeline-track {
    height: 12px; background: #1e1030;
    border-radius: 9999px; overflow: hidden;
}
.pipeline-fill {
    height: 100%; border-radius: 9999px;
    transition: width 0.6s ease;
    background-image: linear-gradient(
        45deg,
        rgba(255,255,255,.15) 25%, transparent 25%,
        transparent 50%, rgba(255,255,255,.15) 50%,
        rgba(255,255,255,.15) 75%, transparent 75%, transparent
    );
    background-size: 1rem 1rem;
    animation: stripe-move 1s linear infinite;
}
@keyframes stripe-move {
    0% { background-position: 1rem 0; }
    100% { background-position: 0 0; }
}
.fill-green {
    background-color: var(--neon-green);
    box-shadow: 0 0 8px var(--neon-green), 0 0 15px rgba(0,255,157,0.25);
}
.fill-blue {
    background-color: var(--neon-blue);
    box-shadow: 0 0 8px var(--neon-blue), 0 0 15px rgba(0,243,255,0.25);
}

/* ═══ PULSE BADGES ═══ */
@keyframes pulse-green {
    0%   { box-shadow: 0 0 0 0 rgba(0,255,157,0.7); }
    70%  { box-shadow: 0 0 0 6px rgba(0,255,157,0); }
    100% { box-shadow: 0 0 0 0 rgba(0,255,157,0); }
}
@keyframes pulse-blue {
    0%   { box-shadow: 0 0 0 0 rgba(0,243,255,0.7); }
    70%  { box-shadow: 0 0 0 6px rgba(0,243,255,0); }
    100% { box-shadow: 0 0 0 0 rgba(0,243,255,0); }
}
.dot-green {
    width: 12px; height: 12px; border-radius: 50%;
    background: var(--neon-green); display: inline-block;
    animation: pulse-green 2s infinite;
}
.dot-blue {
    width: 12px; height: 12px; border-radius: 50%;
    background: var(--neon-blue); display: inline-block;
    animation: pulse-blue 2s infinite;
}
.dot-off {
    width: 12px; height: 12px; border-radius: 50%;
    background: #475569; display: inline-block;
}

/* ═══ WORKER CARDS ═══ */
.wk-card {
    padding: 0.75rem 1rem; border-radius: 0.5rem;
    display: flex; align-items: center; justify-content: space-between;
}
.wk-green { border: 1px solid rgba(0,255,157,0.3); background: rgba(0,255,157,0.04); }
.wk-blue  { border: 1px solid rgba(0,243,255,0.3); background: rgba(0,243,255,0.04); }
.wk-off   { border: 1px solid rgba(71,85,99,0.3);  background: rgba(71,85,99,0.04); }

/* ═══ TERMINAL ═══ */
.terminal-box {
    background: rgba(0,0,0,0.4);
    border: 1px solid var(--border-color);
    border-radius: 0.75rem;
    overflow: hidden; display: flex; flex-direction: column;
}
.terminal-header {
    padding: 0.65rem 1rem;
    border-bottom: 1px solid var(--border-color);
    background: rgba(168,85,247,0.05);
    display: flex; justify-content: space-between; align-items: center;
}
.terminal-dots { display: flex; gap: 6px; }
.terminal-dots span { width: 10px; height: 10px; border-radius: 50%; }
.terminal-body {
    padding: 1rem; font-family: 'Fira Code', monospace;
    font-size: 0.72rem; line-height: 1.75;
    overflow-y: auto; max-height: 360px;
}
.log-i { color: var(--neon-blue); }
.log-s { color: var(--neon-green); }
.log-e { color: var(--neon-red); }
.log-w { color: #eab308; }
.log-d { color: var(--text-muted); }
.log-t { color: var(--text-dim); }

/* ═══ BUTTONS ═══ */
.stButton > button {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 0.5rem !important;
    transition: all 0.15s ease !important;
    letter-spacing: 0.02em !important;
}
.stButton > button:active { transform: scale(0.96) !important; }

/* ═══ FILE UPLOADER ═══ */
section[data-testid="stSidebar"] [data-testid="stFileUploader"] > div {
    border: 2px dashed #475569 !important;
    border-radius: 0.75rem !important;
    background: transparent !important;
    transition: all 0.2s !important;
}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] > div:hover {
    border-color: var(--primary) !important;
    background: rgba(168,85,247,0.04) !important;
}

/* ═══ TABS ═══ */
.stTabs [data-baseweb="tab-list"] {
    gap: 0 !important;
    border-bottom: 1px solid var(--border-color) !important;
    background: transparent !important;
    padding: 0 0.5rem !important;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.85rem !important; font-weight: 500 !important;
    color: var(--text-dim) !important;
    border-bottom: 2px solid transparent !important;
    padding: 0.65rem 1rem !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #fff !important;
    border-bottom-color: var(--primary) !important;
}
.stTabs [data-baseweb="tab-panel"] { padding: 0 !important; }

/* ═══ DATAFRAME ═══ */
[data-testid="stDataFrame"] > div {
    border: none !important;
    background: transparent !important;
}

/* ═══ TOGGLE ═══ */
.stToggle label span {
    font-family: 'Space Grotesk', sans-serif !important;
    color: var(--text-dim) !important; font-size: 0.8rem !important;
}

/* ═══ DOWNLOAD BUTTON ═══ */
.stDownloadButton > button {
    font-family: 'Space Grotesk', sans-serif !important;
    background: var(--primary) !important;
    color: #fff !important; border: none !important;
    font-weight: 600 !important; border-radius: 0.5rem !important;
}

/* ═══ DIVIDERS ═══ */
hr { border-color: rgba(168,85,247,0.12) !important; margin: 0.5rem 0 !important; }

/* ═══ SOURCE BADGES ═══ */
.src-badge {
    display: inline-flex; align-items: center;
    padding: 3px 10px; border-radius: 4px;
    font-size: 0.7rem; font-weight: 600; font-family: 'Fira Code', monospace;
}
.src-sunedu { background: rgba(0,255,157,0.1); color: var(--neon-green); border: 1px solid rgba(0,255,157,0.2); }
.src-minedu { background: rgba(0,243,255,0.1); color: var(--neon-blue); border: 1px solid rgba(0,243,255,0.2); }
.src-error  { background: rgba(255,0,85,0.1); color: var(--neon-red); border: 1px solid rgba(255,0,85,0.2); }
.src-none   { background: rgba(71,85,99,0.15); color: #94a3b8; border: 1px solid rgba(71,85,99,0.3); }

/* ═══ SCROLLBAR ═══ */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #191022; }
::-webkit-scrollbar-thumb { background: #4b5563; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #a855f7; }

/* ═══ SECTION TITLES ═══ */
.sec-title {
    font-size: 0.65rem; text-transform: uppercase;
    letter-spacing: 0.15em; color: var(--text-muted);
    font-weight: 700; margin-bottom: 0.55rem;
}

/* ═══ BLINKING CURSOR ═══ */
@keyframes blink { 0%,100% { opacity:1; } 50% { opacity:0.15; } }
</style>
"""


# ═══════════════════════════════════════════════════════════════════════
#  API HELPERS
# ═══════════════════════════════════════════════════════════════════════

def api_get(path: str, timeout: int = 10) -> Optional[Any]:
    """GET request to the backend API."""
    try:
        r = requests.get(f"{API_BASE_URL}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def api_post(path: str, **kwargs) -> Optional[Dict]:
    """POST request to the backend API."""
    try:
        r = requests.post(f"{API_BASE_URL}{path}", timeout=30, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════
#  RENDER COMPONENTS
# ═══════════════════════════════════════════════════════════════════════

def render_metric_card(label: str, value: int, sub_text: str,
                       sub_color: str, border_class: str, icon: str, icon_color: str):
    """Renders a metric card matching DASHBOARD.HTML style."""
    st.markdown(f"""
    <div class="metric-card {border_class}">
        <div class="mc-icon">
            <span class="material-icons-round" style="font-size:3.5rem; color:{icon_color};">{icon}</span>
        </div>
        <div class="mc-label">{label}</div>
        <div class="mc-value">{value:,}</div>
        <div class="mc-sub" style="color: {sub_color};">
            <span class="material-icons-round" style="font-size:10px;">verified</span>
            {sub_text}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_worker_card(name: str, sub: str, running: bool, color: str):
    """Render sidebar worker status card with animated pulse dot."""
    if running:
        card_cls = "wk-green" if color == "green" else "wk-blue"
        dot_cls = "dot-green" if color == "green" else "dot-blue"
        neon = "var(--neon-green)" if color == "green" else "var(--neon-blue)"
        icon = "school" if color == "green" else "account_balance"
        status_txt = "Scraping Active"
    else:
        card_cls = "wk-off"
        dot_cls = "dot-off"
        neon = "#64748b"
        icon = "school" if color == "green" else "account_balance"
        status_txt = "Stopped"

    st.markdown(f"""
    <div class="wk-card {card_cls}">
        <div style="display:flex; align-items:center; gap:12px;">
            <span class="material-icons-round" style="color:{neon}; font-size:1.4rem;">{icon}</span>
            <div>
                <div style="font-size:0.85rem; font-weight:700; color:#fff;">{name}</div>
                <div style="font-size:0.7rem; color:{neon};">{status_txt}</div>
            </div>
        </div>
        <div class="{dot_cls}"></div>
    </div>
    """, unsafe_allow_html=True)


def render_pipeline_bar(thread_name: str, color: str, pct: float, detail: str):
    """Render animated striped progress bar for the waterfall pipeline."""
    fill_cls = "fill-green" if color == "green" else "fill-blue"
    label_color = "var(--neon-green)" if color == "green" else "var(--neon-blue)"
    pct_clamped = min(max(pct, 0), 100)

    st.markdown(f"""
    <div style="margin-bottom:1.25rem;">
        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <span style="font-family:'Fira Code',monospace; font-size:0.75rem; font-weight:700; color:{label_color};">{thread_name}</span>
            <span style="font-family:'Fira Code',monospace; font-size:0.72rem; color:var(--text-dim);">{detail}</span>
        </div>
        <div class="pipeline-track">
            <div class="pipeline-fill {fill_cls}" style="width:{pct_clamped:.1f}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_terminal(logs: List[Dict]):
    """Render the terminal output panel with colored log lines."""
    lines_html = ""
    for entry in logs[-18:]:
        ts = entry.get("ts", "")
        lvl = entry.get("lvl", "d")
        msg = entry.get("msg", "")
        cls_map = {"i": "log-i", "s": "log-s", "e": "log-e", "w": "log-w", "d": "log-d", "t": "log-t"}
        cls = cls_map.get(lvl, "log-t")
        lines_html += f'<div class="{cls}">[{ts}] {msg}</div>\n'

    lines_html += '<div class="log-s" style="animation:blink 1s infinite;">_</div>'

    st.markdown(f"""
    <div class="terminal-box">
        <div class="terminal-header">
            <span style="font-family:'Fira Code',monospace; font-size:0.72rem; color:var(--text-dim); display:flex; align-items:center; gap:8px;">
                <span class="material-icons-round" style="font-size:14px;">terminal</span>
                TERMINAL_OUTPUT
            </span>
            <div class="terminal-dots">
                <span style="background:var(--neon-red);"></span>
                <span style="background:#eab308;"></span>
                <span style="background:var(--neon-green);"></span>
            </div>
        </div>
        <div class="terminal-body">{lines_html}</div>
    </div>
    """, unsafe_allow_html=True)


def build_terminal_logs(status: Dict, pipeline: Dict, workers: Dict) -> List[Dict]:
    """Build live terminal log entries from current system state."""
    now = datetime.now().strftime("%H:%M:%S")
    logs: List[Dict] = []

    def add(lvl, msg):
        logs.append({"ts": now, "lvl": lvl, "msg": msg})

    s = pipeline.get("sunedu", {})
    m = pipeline.get("minedu", {})
    s_run = workers.get("sunedu", {}).get("running", False)
    m_run = workers.get("minedu", {}).get("running", False)

    add("d", "Initializing parallel workers...")

    if s_run:
        add("i", "[INFO] Worker SUNEDU connected successfully.")
    else:
        add("w", "[WARN] Worker SUNEDU offline.")

    if m_run:
        add("i", "[INFO] Worker MINEDU connected successfully.")
    else:
        add("w", "[WARN] Worker MINEDU offline.")

    total = status.get("total", 0)
    if total > 0:
        add("t", f"Loading batch — {total:,} records parsed.")

    # SUNEDU stats
    sp = s.get("procesando", 0)
    sf = s.get("encontrados", 0)
    sd = s.get("derivados_minedu", 0)
    se = s.get("errores", 0)

    if sp > 0:
        add("t", f"> Starting validation sequence…")
    if sf > 0:
        add("s", f"[FOUND] {sf:,} records verified — SUNEDU DB.")
    if sd > 0:
        add("w", f"[DERIV] {sd:,} DNIs forwarded to MINEDU queue.")
    if se > 0:
        add("e", f"[ERROR] SUNEDU errors: {se}")

    # MINEDU stats
    mp = m.get("procesando", 0)
    mf = m.get("encontrados", 0)
    mn = m.get("no_encontrados", 0)
    me = m.get("errores", 0)

    if mf > 0:
        add("s", f"[FOUND] {mf:,} records verified — MINEDU DB.")
    if mn > 0:
        add("e", f"[NOT_FOUND] {mn:,} DNIs — No records found.")
    if me > 0:
        add("e", f"[ERROR] MINEDU errors: {me}")

    pct = status.get("progreso_pct", 0)
    if total > 0:
        add("d", f"Progress: {pct:.1f}%")

    return logs


# ═══════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title="Validador PRO | Dashboard",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ── Inject CSS ──
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # ── Session State ──
    if "workers_started" not in st.session_state:
        st.session_state.workers_started = False

    # ── Check API connectivity ──
    api_status = api_get("/api/status")
    is_connected = api_status is not None

    # ═══════════════════════════════════════════════════════════════════
    #  SIDEBAR
    # ═══════════════════════════════════════════════════════════════════
    with st.sidebar:
        # ── Branding ──
        st.markdown("""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:2rem;">
            <div style="width:40px; height:40px; border-radius:6px; background:var(--primary);
                        display:flex; align-items:center; justify-content:center;
                        box-shadow:0 0 10px rgba(168,85,247,0.3), 0 0 20px rgba(168,85,247,0.15);">
                <span class="material-icons-round" style="color:#fff; font-size:1.4rem;">verified_user</span>
            </div>
            <div>
                <div style="font-weight:700; font-size:1.05rem; color:#fff; letter-spacing:0.05em;">
                    VALIDADOR <span style="color:var(--primary);">PRO</span>
                </div>
                <div style="font-family:'Fira Code',monospace; font-size:0.65rem; color:var(--text-muted); letter-spacing:0.12em;">
                    v3.0.0 // PIPELINE
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── System Status ──
        st.markdown('<div class="sec-title">System Status</div>', unsafe_allow_html=True)

        workers = api_get("/api/workers/status") or {}
        sunedu_info = workers.get("sunedu", {})
        minedu_info = workers.get("minedu", {})
        sunedu_running = sunedu_info.get("running", False)
        minedu_running = minedu_info.get("running", False)

        render_worker_card("SUNEDU Node", "Universidades", sunedu_running, "green")
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        render_worker_card("MINEDU Node", "Institutos", minedu_running, "blue")

        st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

        # ── Input Source / File Upload ──
        st.markdown('<div class="sec-title">Input Source</div>', unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Drop CSV/XLSX",
            type=["xlsx", "xls", "csv"],
            key="file_uploader",
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            fsize = len(uploaded_file.getvalue()) / 1024
            st.markdown(f"""
            <div style="padding:0.55rem 0.85rem; background:rgba(168,85,247,0.08); border-radius:6px;
                        border:1px solid rgba(168,85,247,0.2); margin:0.4rem 0 0.75rem 0;">
                <div style="font-size:0.8rem; color:#fff; font-weight:500;">{uploaded_file.name}</div>
                <div style="font-size:0.65rem; color:var(--text-muted); font-family:'Fira Code',monospace;">{fsize:.1f} KB</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("⬆ UPLOAD & START", use_container_width=True, type="primary", key="btn_upload"):
                with st.spinner("Uploading file…"):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        r = requests.post(f"{API_BASE_URL}/api/upload", files=files, timeout=60)
                        r.raise_for_status()
                        data = r.json()
                        st.success(f"Batch #{data['lote_id']} — {data['total_dnis']} DNIs loaded")
                        # Auto-start workers if not running
                        if not (sunedu_running or minedu_running):
                            api_post("/api/workers/start")
                        time.sleep(0.8)
                        st.rerun()
                    except requests.HTTPError as e:
                        body = e.response.json() if e.response else {}
                        st.error(body.get("detail", str(e)))
                    except Exception as e:
                        st.error(str(e))

        st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)

        # ── Controls ──
        st.markdown('<div class="sec-title">Controls</div>', unsafe_allow_html=True)

        if st.button("▶ START PIPELINE", use_container_width=True, type="primary", key="btn_start"):
            with st.spinner("Iniciando workers…"):
                res = api_post("/api/workers/start")
                if res:
                    st.session_state.workers_started = True
                    st.success("Workers started")
                    time.sleep(0.5)
                    st.rerun()

        col_stop, col_clear = st.columns(2)
        with col_stop:
            if st.button("⏹ STOP", use_container_width=True, key="btn_stop"):
                with st.spinner("Stopping…"):
                    res = api_post("/api/workers/stop")
                    if res:
                        st.session_state.workers_started = False
                        st.warning("Workers stopped")
                        time.sleep(0.5)
                        st.rerun()
        with col_clear:
            if st.button("🗑 CLEAR", use_container_width=True, key="btn_clear"):
                with st.spinner("Clearing…"):
                    res = api_post("/api/limpiar")
                    if res:
                        st.session_state.workers_started = False
                        st.success(f"Cleared {res.get('registros_eliminados', 0)} records")
                        time.sleep(0.5)
                        st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        auto_refresh = st.toggle("Auto-refresh (2s)", value=True, key="auto_refresh")

        if st.button("↻ Refresh now", use_container_width=True, key="btn_refresh"):
            st.rerun()

        # ── Footer ──
        st.markdown("""
        <div style="position:absolute; bottom:0; left:0; right:0;
                    padding:1rem; border-top:1px solid rgba(30,20,40,0.6);
                    text-align:center;">
            <span style="font-family:'Fira Code',monospace; font-size:0.6rem; color:var(--text-muted); letter-spacing:0.1em;">
                SECURE CONNECTION // TLS 1.3
            </span>
        </div>
        """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════
    #  MAIN CONTENT AREA
    # ═══════════════════════════════════════════════════════════════════

    if not is_connected:
        st.markdown("""
        <div style="text-align:center; padding:5rem 2rem;">
            <span class="material-icons-round" style="font-size:4rem; color:var(--neon-red); margin-bottom:1rem; display:block;">wifi_off</span>
            <div style="font-size:1.8rem; font-weight:700; color:var(--neon-red); margin-bottom:0.75rem;">CONNECTION FAILED</div>
            <div style="color:var(--text-dim); font-size:0.9rem; line-height:1.8;">
                Cannot reach API at <code style="color:var(--primary);">http://127.0.0.1:8000</code><br>
                Start the backend: <code style="color:var(--neon-green);">python api.py</code>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    # ── Extract data from API ──
    status = api_status or {}
    total = status.get("total", 0)
    terminados = status.get("terminados", 0)
    progreso = status.get("progreso_pct", 0)
    conteos = status.get("conteos", {})
    pipeline = status.get("pipeline", {})

    found_sunedu = conteos.get("FOUND_SUNEDU", 0)
    found_minedu = conteos.get("FOUND_MINEDU", 0)
    not_found = conteos.get("NOT_FOUND", 0)
    err_s = conteos.get("ERROR_SUNEDU", 0)
    err_m = conteos.get("ERROR_MINEDU", 0)
    total_errors = err_s + err_m

    # ════════════════════════════════════════════════════════════════
    #  ROW 1 — METRIC CARDS
    # ════════════════════════════════════════════════════════════════
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        pct_txt = f"{progreso:.1f}% done" if total > 0 else "No data"
        render_metric_card("Total Processed", total, pct_txt,
                           "var(--primary)", "border-l-primary", "analytics", "var(--primary)")
    with c2:
        s_txt = f"{found_sunedu/total*100:.1f}% Valid" if total > 0 else "—"
        render_metric_card("Found SUNEDU", found_sunedu, s_txt,
                           "var(--neon-green)", "border-l-green", "check_circle", "var(--neon-green)")
    with c3:
        m_txt = f"{found_minedu/total*100:.1f}% Valid" if total > 0 else "—"
        render_metric_card("Found MINEDU", found_minedu, m_txt,
                           "var(--neon-blue)", "border-l-blue", "fact_check", "var(--neon-blue)")
    with c4:
        nf_txt = f"{not_found/total*100:.1f}% Invalid" if total > 0 else "—"
        render_metric_card("Not Found", not_found, nf_txt,
                           "var(--neon-red)", "border-l-red", "error_outline", "var(--neon-red)")

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    #  ROW 2 — WATERFALL PIPELINE
    # ════════════════════════════════════════════════════════════════
    s_pipe = pipeline.get("sunedu", {})
    m_pipe = pipeline.get("minedu", {})

    s_pend = s_pipe.get("pendientes", 0)
    s_proc = s_pipe.get("procesando", 0)
    s_found = s_pipe.get("encontrados", 0)
    s_deriv = s_pipe.get("derivados_minedu", 0)
    s_err = s_pipe.get("errores", 0)
    s_total = s_pend + s_proc + s_found + s_deriv + s_err
    s_done = s_found + s_deriv + s_err
    s_pct = (s_done / s_total * 100) if s_total > 0 else 0

    m_pend = m_pipe.get("pendientes", 0)
    m_proc = m_pipe.get("procesando", 0)
    m_found = m_pipe.get("encontrados", 0)
    m_nf = m_pipe.get("no_encontrados", 0)
    m_err = m_pipe.get("errores", 0)
    m_total = m_pend + m_proc + m_found + m_nf + m_err
    m_done = m_found + m_nf + m_err
    m_pct = (m_done / m_total * 100) if m_total > 0 else 0

    # Lotes info for batch ID display
    lotes = api_get("/api/lotes") or []
    batch_label = f"BATCH ID: #{lotes[0]['id']}" if lotes else "NO BATCH"

    st.markdown(f"""
    <div class="glass-panel" style="margin-bottom:0.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
            <div style="font-size:1rem; font-weight:700; color:#fff; display:flex; align-items:center; gap:8px;">
                <span class="material-icons-round" style="color:var(--primary);">waterfall_chart</span>
                Waterfall Pipeline
            </div>
            <span style="font-family:'Fira Code',monospace; font-size:0.7rem; color:var(--text-muted);">{batch_label}</span>
        </div>
    """, unsafe_allow_html=True)

    render_pipeline_bar(
        "THREAD_A::SUNEDU", "green", s_pct,
        f"{s_done}/{s_total} ({s_pct:.0f}%)" if s_total > 0 else "Idle"
    )
    render_pipeline_bar(
        "THREAD_B::MINEDU", "blue", m_pct,
        f"{m_done}/{m_total} ({m_pct:.0f}%)" if m_total > 0 else "Idle"
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    #  ROW 3 — TERMINAL + DATA TABLE
    # ════════════════════════════════════════════════════════════════
    col_term, col_table = st.columns([1, 2])

    # ── Terminal Logs ──
    with col_term:
        log_entries = build_terminal_logs(status, pipeline, workers)
        render_terminal(log_entries)

    # ── Data Table ──
    with col_table:
        tab_all, tab_sunedu, tab_minedu, tab_nf, tab_err = st.tabs([
            "All Records",
            f"SUNEDU  ({found_sunedu})",
            f"MINEDU  ({found_minedu})",
            f"Not Found  ({not_found})",
            f"Errors  ({total_errors})",
        ])

        with tab_all:
            _render_tab_all()

        with tab_sunedu:
            _render_tab_sunedu()

        with tab_minedu:
            _render_tab_minedu()

        with tab_nf:
            _render_tab_notfound()

        with tab_err:
            _render_tab_errors()

        # ── Footer Bar: Download + Info ──
        st.markdown("<div style='height:0.35rem;'></div>", unsafe_allow_html=True)
        dl_col, info_col = st.columns([1, 3])

        with dl_col:
            if total > 0:
                try:
                    r = requests.get(f"{API_BASE_URL}/api/resultados", timeout=30)
                    if r.status_code == 200:
                        st.download_button(
                            label="⬇ Download Excel",
                            data=r.content,
                            file_name=f"resultados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )
                except Exception:
                    pass

        with info_col:
            st.markdown(f"""
            <div style="font-family:'Fira Code',monospace; font-size:0.7rem; color:var(--text-muted);
                        padding-top:0.6rem;">
                Showing records from {total:,} total // Last update: {datetime.now().strftime('%H:%M:%S')}
            </div>
            """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════
    #  AUTO-REFRESH
    # ════════════════════════════════════════════════════════════════
    s_pend_v = pipeline.get("sunedu", {}).get("pendientes", 0)
    m_pend_v = pipeline.get("minedu", {}).get("pendientes", 0)
    s_proc_v = pipeline.get("sunedu", {}).get("procesando", 0)
    m_proc_v = pipeline.get("minedu", {}).get("procesando", 0)
    processing = s_pend_v > 0 or m_pend_v > 0 or s_proc_v > 0 or m_proc_v > 0

    if auto_refresh and processing:
        time.sleep(POLL_INTERVAL)
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════
#  TAB RENDERERS
# ═══════════════════════════════════════════════════════════════════════

def _render_tab_all():
    """All Records tab — shows every record with source badges."""
    records = api_get("/api/registros?limit=200") or []
    if not records:
        _empty_state("No records loaded yet. Upload a file to begin.")
        return

    df = pd.DataFrame(records)

    # Build display name
    if "sunedu_nombres" in df.columns and "minedu_nombres" in df.columns:
        df["nombre"] = df.apply(
            lambda r: r.get("sunedu_nombres") or r.get("minedu_nombres") or "—", axis=1
        )
    elif "sunedu_nombres" in df.columns:
        df["nombre"] = df["sunedu_nombres"].fillna("—")
    elif "minedu_nombres" in df.columns:
        df["nombre"] = df["minedu_nombres"].fillna("—")
    else:
        df["nombre"] = "—"

    # Institution
    if "sunedu_institucion" in df.columns and "minedu_institucion" in df.columns:
        df["institucion"] = df.apply(
            lambda r: r.get("sunedu_institucion") or r.get("minedu_institucion") or "—", axis=1
        )
    elif "sunedu_institucion" in df.columns:
        df["institucion"] = df["sunedu_institucion"].fillna("—")
    elif "minedu_institucion" in df.columns:
        df["institucion"] = df["minedu_institucion"].fillna("—")
    else:
        df["institucion"] = "—"

    cols = ["id", "dni", "nombre", "institucion", "estado", "error_msg"]
    cols_ok = [c for c in cols if c in df.columns]
    rename = {
        "id": "ID", "dni": "DNI", "nombre": "Full Name",
        "institucion": "Institution", "estado": "Source", "error_msg": "Detail",
    }
    display = df[cols_ok].rename(columns={k: v for k, v in rename.items() if k in cols_ok})
    st.dataframe(display.head(100), use_container_width=True, hide_index=True, height=360)


def _render_tab_sunedu():
    """SUNEDU tab — verified university degrees."""
    records = api_get("/api/registros?estado=FOUND_SUNEDU&limit=200") or []
    if not records:
        _empty_state("No SUNEDU records found yet.")
        return

    df = pd.DataFrame(records)
    cols = ["dni", "sunedu_nombres", "sunedu_grado", "sunedu_institucion", "sunedu_fecha_diploma"]
    cols_ok = [c for c in cols if c in df.columns]
    rename = {
        "dni": "DNI", "sunedu_nombres": "Full Name", "sunedu_grado": "Degree",
        "sunedu_institucion": "Institution", "sunedu_fecha_diploma": "Diploma Date",
    }
    display = df[cols_ok].rename(columns={k: v for k, v in rename.items() if k in cols_ok})
    st.dataframe(display.head(100), use_container_width=True, hide_index=True, height=360)


def _render_tab_minedu():
    """MINEDU tab — verified institute titles."""
    records = api_get("/api/registros?estado=FOUND_MINEDU&limit=200") or []
    if not records:
        _empty_state("No MINEDU records found yet.")
        return

    df = pd.DataFrame(records)
    cols = ["dni", "minedu_nombres", "minedu_titulo", "minedu_institucion", "minedu_fecha"]
    cols_ok = [c for c in cols if c in df.columns]
    rename = {
        "dni": "DNI", "minedu_nombres": "Full Name", "minedu_titulo": "Title",
        "minedu_institucion": "Institution", "minedu_fecha": "Date",
    }
    display = df[cols_ok].rename(columns={k: v for k, v in rename.items() if k in cols_ok})
    st.dataframe(display.head(100), use_container_width=True, hide_index=True, height=360)


def _render_tab_notfound():
    """Not Found tab."""
    records = api_get("/api/registros?estado=NOT_FOUND&limit=200") or []
    if not records:
        _empty_state("No unmatched records yet.")
        return

    df = pd.DataFrame(records)
    cols = ["dni", "error_msg", "updated_at"]
    cols_ok = [c for c in cols if c in df.columns]
    rename = {"dni": "DNI", "error_msg": "Reason", "updated_at": "Timestamp"}
    display = df[cols_ok].rename(columns={k: v for k, v in rename.items() if k in cols_ok})
    st.dataframe(display.head(100), use_container_width=True, hide_index=True, height=360)


def _render_tab_errors():
    """Errors tab with motivo summary + table."""
    err_s_recs = api_get("/api/registros?estado=ERROR_SUNEDU&limit=100") or []
    err_m_recs = api_get("/api/registros?estado=ERROR_MINEDU&limit=100") or []
    all_errs = err_s_recs + err_m_recs

    if not all_errs:
        st.markdown("""
        <div style="padding:2rem; text-align:center;">
            <span class="material-icons-round" style="font-size:2.5rem; color:var(--neon-green); margin-bottom:0.5rem; display:block;">check_circle</span>
            <div style="color:var(--neon-green); font-size:0.9rem; font-weight:600;">No errors registered</div>
            <div style="color:var(--text-muted); font-size:0.75rem; margin-top:0.25rem;">Pipeline running clean</div>
        </div>
        """, unsafe_allow_html=True)
        return

    df = pd.DataFrame(all_errs)

    # Error summary by motivo
    if "error_msg" in df.columns:
        motivos = df["error_msg"].dropna().value_counts().head(8)
        if not motivos.empty:
            summary = ""
            for motivo, count in motivos.items():
                short = str(motivo)[:90]
                summary += f"""
                <div style="display:flex; justify-content:space-between; padding:0.4rem 0.7rem;
                            background:rgba(255,0,85,0.06); border-left:3px solid var(--neon-red);
                            margin-bottom:3px; border-radius:0 4px 4px 0; font-size:0.72rem;">
                    <span style="color:var(--text-dim);">{short}</span>
                    <span style="color:var(--neon-red); font-weight:700; font-family:'Fira Code',monospace;">{count}</span>
                </div>
                """
            st.markdown(f'<div style="margin-bottom:0.75rem;">{summary}</div>', unsafe_allow_html=True)

    cols = ["dni", "estado", "error_msg", "updated_at"]
    cols_ok = [c for c in cols if c in df.columns]
    rename = {"dni": "DNI", "estado": "Worker", "error_msg": "Error Detail", "updated_at": "Timestamp"}
    display = df[cols_ok].rename(columns={k: v for k, v in rename.items() if k in cols_ok})
    st.dataframe(display.head(100), use_container_width=True, hide_index=True, height=280)


def _empty_state(message: str):
    """Render an empty state placeholder."""
    st.markdown(f"""
    <div style="padding:2.5rem; text-align:center;">
        <span class="material-icons-round" style="font-size:2.5rem; color:var(--text-muted); margin-bottom:0.5rem; display:block;">inbox</span>
        <div style="color:var(--text-dim); font-size:0.85rem;">{message}</div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()

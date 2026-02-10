"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  VALIDADOR DE GRADOS ACADÉMICOS - DASHBOARD ELITE v2.0                       ║
║  Pipeline ETL: SUNEDU → MINEDU | Interfaz Brutal SaaS Dark Mode              ║
║                                                                              ║
║  Características:                                                            ║
║  • Dark Mode Cyberpunk con Glassmorphism                                     ║
║  • Animaciones Lottie en tiempo real                                         ║
║  • Métricas vivas con auto-refresh (polling 2s)                              ║
║  • Consola de logs estilo terminal hacker                                    ║
║  • Visualización Waterfall del Pipeline                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
import io
import time
import json
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any, List

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN Y CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

API_BASE_URL = "http://127.0.0.1:8000"
POLL_INTERVAL = 2  # segundos

# URLs de animaciones Lottie (gratuitas de LottieFiles)
LOTTIE_ANIMATIONS = {
    "robot_search": "https://lottie.host/5f6e6e6e-5f6e-5f6e-5f6e-5f6e5f6e5f6e/robot.json",  # Fallback: usaremos embed
    "success_check": "https://assets2.lottiefiles.com/packages/lf20_s2lryxtd.json",
    "loading": "https://assets9.lottiefiles.com/packages/lf20_b88nh30c.json",
    "upload": "https://assets3.lottiefiles.com/packages/lf20_j1adxtyb.json",
    "data_processing": "https://assets5.lottiefiles.com/packages/lf20_w51pcehl.json",
    "rocket": "https://assets1.lottiefiles.com/packages/lf20_96bovdur.json",
}

# CSS Inline para animaciones Lottie fallback
LOTTIE_CSS = """
<style>
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 20px rgba(0, 255, 136, 0.3); }
    50% { box-shadow: 0 0 40px rgba(0, 255, 136, 0.6); }
}
@keyframes scanline {
    0% { transform: translateY(-100%); }
    100% { transform: translateY(100%); }
}
@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}
@keyframes slideIn {
    from { opacity: 0; transform: translateY(-20px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes gradient-shift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
@keyframes spin-slow {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
</style>
"""

# ═══════════════════════════════════════════════════════════════════════════════
# CSS PERSONALIZADO BRUTAL - DARK MODE + GLASSMORPHISM
# ═══════════════════════════════════════════════════════════════════════════════

CUSTOM_CSS = """
<style>
/* ═══════════════════════════════════════════════════════════════════════════ */
/* RESET Y CONFIGURACIÓN GLOBAL */
/* ═══════════════════════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --color-bg-primary: #0a0a0f;
    --color-bg-secondary: #12121a;
    --color-bg-glass: rgba(20, 20, 35, 0.7);
    --color-border: rgba(100, 100, 255, 0.15);
    --color-border-glow: rgba(0, 255, 136, 0.4);
    --color-text-primary: #e8e8ff;
    --color-text-secondary: #9090b0;
    --color-accent-cyan: #00d4ff;
    --color-accent-green: #00ff88;
    --color-accent-purple: #a855f7;
    --color-accent-orange: #ff6b35;
    --color-accent-red: #ff4757;
    --color-accent-blue: #3b82f6;
    --font-mono: 'JetBrains Mono', monospace;
    --font-sans: 'Inter', sans-serif;
}

/* Ocultar elementos de Streamlit */
#MainMenu {visibility: hidden !important;}
footer {visibility: hidden !important;}
header {visibility: hidden !important;}
.stDeployButton {display: none !important;}

/* Fondo animado */
.stApp {
    background: linear-gradient(135deg, #0a0a0f 0%, #12121a 50%, #0d0d15 100%);
    background-attachment: fixed;
    font-family: var(--font-sans);
}

/* Efecto de grid sutil */
.stApp::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image: 
        linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
    background-size: 50px 50px;
    pointer-events: none;
    z-index: 0;
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* TIPOGRAFÍA */
/* ═══════════════════════════════════════════════════════════════════════════ */
h1, h2, h3 {
    font-family: var(--font-sans) !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}

.cyber-title {
    background: linear-gradient(90deg, var(--color-accent-cyan), var(--color-accent-purple), var(--color-accent-green));
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradient-shift 3s ease infinite;
    text-shadow: 0 0 30px rgba(0, 212, 255, 0.3);
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* CONTENEDORES - GLASSMORPHISM */
/* ═══════════════════════════════════════════════════════════════════════════ */
.glass-container {
    background: var(--color-bg-glass) !important;
    backdrop-filter: blur(20px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
    border: 1px solid var(--color-border) !important;
    border-radius: 16px !important;
    box-shadow: 
        0 8px 32px rgba(0, 0, 0, 0.4),
        inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
    padding: 1.5rem;
    transition: all 0.3s ease;
}

.glass-container:hover {
    border-color: var(--color-border-glow) !important;
    box-shadow: 
        0 12px 48px rgba(0, 0, 0, 0.5),
        0 0 20px rgba(0, 255, 136, 0.1),
        inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* BOTONES ESTILIZADOS */
/* ═══════════════════════════════════════════════════════════════════════════ */
.stButton > button {
    background: linear-gradient(135deg, rgba(0, 212, 255, 0.15), rgba(168, 85, 247, 0.15)) !important;
    border: 1px solid rgba(0, 212, 255, 0.3) !important;
    border-radius: 12px !important;
    color: var(--color-text-primary) !important;
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    padding: 0.75rem 1.5rem !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    font-size: 0.85rem !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, rgba(0, 212, 255, 0.25), rgba(168, 85, 247, 0.25)) !important;
    border-color: var(--color-accent-cyan) !important;
    box-shadow: 0 0 20px rgba(0, 212, 255, 0.3) !important;
    transform: translateY(-2px) !important;
}

.stButton > button:active {
    transform: translateY(0) !important;
}

/* Botón principal - INICIAR MOTOR */
.btn-motor {
    background: linear-gradient(135deg, #00ff88, #00d4ff) !important;
    border: none !important;
    color: #000 !important;
    font-weight: 800 !important;
    font-size: 1.1rem !important;
    padding: 1rem 2rem !important;
    animation: pulse-glow 2s infinite;
}

.btn-motor:hover {
    background: linear-gradient(135deg, #00ffa0, #00e5ff) !important;
    box-shadow: 0 0 40px rgba(0, 255, 136, 0.5) !important;
}

/* Botón de peligro - Detener */
.btn-danger {
    background: linear-gradient(135deg, rgba(255, 71, 87, 0.2), rgba(255, 107, 53, 0.2)) !important;
    border-color: rgba(255, 71, 87, 0.4) !important;
}

.btn-danger:hover {
    background: linear-gradient(135deg, rgba(255, 71, 87, 0.3), rgba(255, 107, 53, 0.3)) !important;
    border-color: #ff4757 !important;
    box-shadow: 0 0 20px rgba(255, 71, 87, 0.3) !important;
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* FILE UPLOADER ESTILIZADO */
/* ═══════════════════════════════════════════════════════════════════════════ */
.stFileUploader > div {
    background: rgba(10, 10, 15, 0.6) !important;
    border: 2px dashed rgba(0, 212, 255, 0.3) !important;
    border-radius: 16px !important;
    padding: 2rem !important;
    transition: all 0.3s ease !important;
}

.stFileUploader > div:hover {
    border-color: var(--color-accent-cyan) !important;
    background: rgba(0, 212, 255, 0.05) !important;
    box-shadow: 0 0 30px rgba(0, 212, 255, 0.1) !important;
}

.stFileUploader > div > div {
    color: var(--color-text-secondary) !important;
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* BARRAS DE PROGRESO PERSONALIZADAS */
/* ═══════════════════════════════════════════════════════════════════════════ */
st.progress > div > div {
    background: linear-gradient(90deg, var(--color-accent-cyan), var(--color-accent-green)) !important;
    border-radius: 10px !important;
    box-shadow: 0 0 10px rgba(0, 255, 136, 0.3) !important;
}

.progress-container {
    background: rgba(0, 0, 0, 0.4) !important;
    border-radius: 12px !important;
    padding: 0.75rem 1rem !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
}

.progress-bar-custom {
    height: 8px !important;
    background: rgba(255, 255, 255, 0.1) !important;
    border-radius: 4px !important;
    overflow: hidden !important;
    position: relative !important;
}

.progress-bar-fill {
    height: 100% !important;
    border-radius: 4px !important;
    transition: width 0.5s ease !important;
    position: relative !important;
}

.progress-bar-fill::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
    animation: shimmer 2s infinite;
}

@keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* MÉTRICAS ESTILIZADAS */
/* ═══════════════════════════════════════════════════════════════════════════ */
.metric-card {
    background: linear-gradient(135deg, rgba(20, 20, 35, 0.8), rgba(30, 30, 50, 0.6)) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 16px !important;
    padding: 1.25rem !important;
    text-align: center !important;
    transition: all 0.3s ease !important;
    position: relative !important;
    overflow: hidden !important;
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
}

.metric-card:hover {
    transform: translateY(-3px) !important;
    border-color: rgba(255, 255, 255, 0.15) !important;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4) !important;
}

.metric-value {
    font-family: var(--font-mono) !important;
    font-size: 2.5rem !important;
    font-weight: 700 !important;
    background: linear-gradient(180deg, #fff, rgba(255,255,255,0.7));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.metric-label {
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    color: var(--color-text-secondary) !important;
    margin-top: 0.5rem !important;
}

/* Colores de acento para métricas */
.metric-total { --accent: #a855f7; border-top-color: #a855f7 !important; }
.metric-sunedu { --accent: #00ff88; border-top-color: #00ff88 !important; }
.metric-minedu { --accent: #3b82f6; border-top-color: #3b82f6 !important; }
.metric-notfound { --accent: #ff4757; border-top-color: #ff4757 !important; }

/* ═══════════════════════════════════════════════════════════════════════════ */
/* CONSOLA DE LOGS - TERMINAL HACKER */
/* ═══════════════════════════════════════════════════════════════════════════ */
.terminal-container {
    background: #0d0d12 !important;
    border: 1px solid rgba(0, 255, 136, 0.2) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    font-family: var(--font-mono) !important;
    position: relative !important;
    overflow: hidden !important;
}

.terminal-container::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 30px;
    background: linear-gradient(180deg, rgba(0, 255, 136, 0.05), transparent);
    pointer-events: none;
}

.terminal-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid rgba(0, 255, 136, 0.1);
    margin-bottom: 0.75rem;
}

.terminal-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
}

.terminal-dot.red { background: #ff5f56; }
.terminal-dot.yellow { background: #ffbd2e; }
.terminal-dot.green { background: #27c93f; }

.terminal-title {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.5);
    margin-left: 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.terminal-body {
    max-height: 250px;
    overflow-y: auto;
}

.terminal-line {
    font-size: 0.8rem;
    line-height: 1.6;
    padding: 0.2rem 0;
    border-left: 2px solid transparent;
    padding-left: 0.5rem;
    margin-left: -0.5rem;
}

.terminal-line:hover {
    background: rgba(0, 255, 136, 0.05);
    border-left-color: rgba(0, 255, 136, 0.3);
}

.terminal-timestamp {
    color: #666;
    margin-right: 0.5rem;
}

.terminal-level-info { color: #00d4ff; }
.terminal-level-success { color: #00ff88; }
.terminal-level-warning { color: #ffbd2e; }
.terminal-level-error { color: #ff5f56; }

.terminal-cursor {
    display: inline-block;
    width: 8px;
    height: 15px;
    background: #00ff88;
    animation: blink 1s infinite;
    vertical-align: middle;
    margin-left: 0.25rem;
}

/* Scrollbar terminal */
.terminal-body::-webkit-scrollbar {
    width: 6px;
}

.terminal-body::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.3);
}

.terminal-body::-webkit-scrollbar-thumb {
    background: rgba(0, 255, 136, 0.3);
    border-radius: 3px;
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* STATUS INDICATORS */
/* ═══════════════════════════════════════════════════════════════════════════ */
.status-indicator {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.8rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.status-online {
    background: rgba(0, 255, 136, 0.15);
    color: #00ff88;
    border: 1px solid rgba(0, 255, 136, 0.3);
}

.status-offline {
    background: rgba(255, 71, 87, 0.15);
    color: #ff4757;
    border: 1px solid rgba(255, 71, 87, 0.3);
}

.status-processing {
    background: rgba(0, 212, 255, 0.15);
    color: #00d4ff;
    border: 1px solid rgba(0, 212, 255, 0.3);
}

.pulse-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse-dot 1.5s infinite;
}

@keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.8); }
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* PIPELINE WATERFALL */
/* ═══════════════════════════════════════════════════════════════════════════ */
.pipeline-stage {
    background: rgba(20, 20, 35, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 1rem;
    position: relative;
    transition: all 0.3s ease;
}

.pipeline-stage.active {
    border-color: rgba(0, 212, 255, 0.4);
    box-shadow: 0 0 20px rgba(0, 212, 255, 0.1);
}

.pipeline-stage.completed {
    border-color: rgba(0, 255, 136, 0.4);
}

.pipeline-connector {
    position: absolute;
    right: -20px;
    top: 50%;
    transform: translateY(-50%);
    width: 20px;
    height: 2px;
    background: linear-gradient(90deg, rgba(255,255,255,0.2), transparent);
}

.pipeline-arrow {
    color: rgba(255, 255, 255, 0.3);
    font-size: 1.2rem;
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* TABLAS ESTILIZADAS */
/* ═══════════════════════════════════════════════════════════════════════════ */
.dataframe {
    background: rgba(10, 10, 15, 0.6) !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    overflow: hidden !important;
}

.dataframe th {
    background: rgba(20, 20, 35, 0.8) !important;
    color: var(--color-accent-cyan) !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.05em !important;
    padding: 1rem !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
}

.dataframe td {
    color: var(--color-text-primary) !important;
    padding: 0.875rem 1rem !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
    font-size: 0.9rem !important;
}

.dataframe tr:hover td {
    background: rgba(0, 212, 255, 0.05) !important;
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* BADGES Y TAGS */
/* ═══════════════════════════════════════════════════════════════════════════ */
.badge {
    display: inline-block;
    padding: 0.25rem 0.6rem;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.badge-sunedu { background: rgba(0, 255, 136, 0.15); color: #00ff88; }
.badge-minedu { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
.badge-error { background: rgba(255, 71, 87, 0.15); color: #ff4757; }
.badge-pending { background: rgba(255, 189, 46, 0.15); color: #ffbd2e; }
.badge-success { background: rgba(0, 255, 136, 0.15); color: #00ff88; }

/* ═══════════════════════════════════════════════════════════════════════════ */
/* ANIMACIONES DE CARGA */
/* ═══════════════════════════════════════════════════════════════════════════ */
.spinner-cyber {
    width: 50px;
    height: 50px;
    border: 3px solid rgba(0, 212, 255, 0.1);
    border-top-color: var(--color-accent-cyan);
    border-radius: 50%;
    animation: spin-slow 1s linear infinite;
}

.loading-text {
    font-family: var(--font-mono);
    color: var(--color-accent-cyan);
    font-size: 0.875rem;
    animation: pulse-text 1.5s infinite;
}

@keyframes pulse-text {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* DIVIDERS */
/* ═══════════════════════════════════════════════════════════════════════════ */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent) !important;
    margin: 2rem 0 !important;
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* EXPANDER ESTILIZADO */
/* ═══════════════════════════════════════════════════════════════════════════ */
.streamlit-expander {
    background: rgba(20, 20, 35, 0.5) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}

.streamlit-expanderHeader {
    background: rgba(30, 30, 50, 0.5) !important;
    color: var(--color-text-primary) !important;
    font-weight: 600 !important;
    padding: 1rem 1.25rem !important;
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* CHECKBOX Y TOGGLES */
/* ═══════════════════════════════════════════════════════════════════════════ */
.stCheckbox > label {
    color: var(--color-text-secondary) !important;
    font-size: 0.875rem !important;
}

.stCheckbox > div[role="checkbox"] {
    background: rgba(20, 20, 35, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* RESPONSIVE */
/* ═══════════════════════════════════════════════════════════════════════════ */
@media (max-width: 768px) {
    .metric-value {
        font-size: 1.75rem !important;
    }
    .glass-container {
        padding: 1rem !important;
    }
}
</style>
"""

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def api_get(path: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """GET request a la API."""
    try:
        r = requests.get(f"{API_BASE_URL}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.ConnectionError:
        return None
    except Exception as e:
        st.error(f"Error API: {e}")
        return None

def api_post(path: str, **kwargs) -> Optional[Dict[str, Any]]:
    """POST request a la API."""
    try:
        r = requests.post(f"{API_BASE_URL}{path}", timeout=30, **kwargs)
        r.raise_for_status()
        return r.json()
    except requests.ConnectionError:
        return None
    except Exception as e:
        st.error(f"Error API: {e}")
        return None

def get_lottie_html(url: str, height: int = 150) -> str:
    """Genera HTML para animación Lottie."""
    return f"""
    <div style="display: flex; justify-content: center; align-items: center; height: {height}px;">
        <dotlottie-player 
            src="{url}" 
            background="transparent" 
            speed="1" 
            style="width: {height}px; height: {height}px;" 
            loop 
            autoplay>
        </dotlottie-player>
    </div>
    """

def get_animated_icon(icon_type: str, size: int = 60) -> str:
    """Genera iconos animados con CSS puro."""
    icons = {
        "search": f"""
            <div style="width: {size}px; height: {size}px; position: relative;">
                <svg viewBox="0 0 24 24" fill="none" stroke="#00d4ff" stroke-width="2" 
                     style="width: 100%; height: 100%; animation: pulse-glow 2s infinite;">
                    <circle cx="11" cy="11" r="8"/>
                    <path d="m21 21-4.35-4.35"/>
                </svg>
                <div style="position: absolute; bottom: 0; right: 0; width: 12px; height: 12px; 
                            background: #00ff88; border-radius: 50%; animation: pulse-dot 1s infinite;"></div>
            </div>
        """,
        "success": f"""
            <div style="width: {size}px; height: {size}px;">
                <svg viewBox="0 0 24 24" fill="none" stroke="#00ff88" stroke-width="2.5"
                     style="width: 100%; height: 100%; animation: slideIn 0.5s ease;">
                    <path d="M20 6L9 17l-5-5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
        """,
        "rocket": f"""
            <div style="width: {size}px; height: {size}px;">
                <svg viewBox="0 0 24 24" fill="none" stroke="#a855f7" stroke-width="2"
                     style="width: 100%; height: 100%; animation: pulse-glow 2s infinite;">
                    <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/>
                    <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/>
                    <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/>
                    <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>
                </svg>
            </div>
        """,
        "database": f"""
            <div style="width: {size}px; height: {size}px;">
                <svg viewBox="0 0 24 24" fill="none" stroke="#00d4ff" stroke-width="2"
                     style="width: 100%; height: 100%;">
                    <ellipse cx="12" cy="5" rx="9" ry="3"/>
                    <path d="M3 5V19A9 3 0 0 0 21 19V5"/>
                    <path d="M3 12A9 3 0 0 0 21 12"/>
                </svg>
            </div>
        """,
        "worker": f"""
            <div style="width: {size}px; height: {size}px;">
                <svg viewBox="0 0 24 24" fill="none" stroke="#ffbd2e" stroke-width="2"
                     style="width: 100%; height: 100%; animation: spin-slow 4s linear infinite;">
                    <circle cx="12" cy="12" r="3"/>
                    <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
                </svg>
            </div>
        """,
    }
    return icons.get(icon_type, icons["search"])

def format_timestamp(iso_str: str) -> str:
    """Formatea timestamp ISO a formato legible."""
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return dt.strftime('%H:%M:%S')
    except:
        return iso_str[:8] if iso_str else '--:--:--'

def get_status_color(estado: str) -> str:
    """Retorna clase CSS según estado."""
    colors = {
        'FOUND_SUNEDU': 'badge-sunedu',
        'FOUND_MINEDU': 'badge-minedu',
        'PENDIENTE': 'badge-pending',
        'CHECK_MINEDU': 'badge-pending',
        'NOT_FOUND': 'badge-error',
        'ERROR_SUNEDU': 'badge-error',
        'ERROR_MINEDU': 'badge-error',
        'PROCESANDO_SUNEDU': 'badge-sunedu',
        'PROCESANDO_MINEDU': 'badge-minedu',
    }
    return colors.get(estado, 'badge-pending')

# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENTES UI REUTILIZABLES
# ═══════════════════════════════════════════════════════════════════════════════

def render_metric_card(label: str, value: int, accent_color: str, icon: str, delta: Optional[str] = None):
    """Renderiza una tarjeta de métrica estilizada."""
    delta_html = f'<div style="font-size: 0.75rem; color: {accent_color}; margin-top: 0.25rem;">{delta}</div>' if delta else ''
    
    html = f"""
    <div class="metric-card metric-{icon}" style="border-top: 2px solid {accent_color};">
        <div style="font-size: 2rem; font-weight: 800; color: {accent_color}; font-family: 'JetBrains Mono', monospace;">
            {value:,}
        </div>
        <div class="metric-label" style="color: rgba(255,255,255,0.6);">{label}</div>
        {delta_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_progress_bar(label: str, current: int, total: int, color1: str, color2: str, status_text: str = ""):
    """Renderiza una barra de progreso personalizada."""
    pct = (current / total * 100) if total > 0 else 0
    
    html = f"""
    <div style="margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
            <span style="font-weight: 600; color: {color1}; font-size: 0.875rem;">{label}</span>
            <span style="font-family: 'JetBrains Mono', monospace; color: rgba(255,255,255,0.7); font-size: 0.875rem;">
                {current}/{total} ({pct:.1f}%)
            </span>
        </div>
        <div class="progress-bar-custom" style="height: 10px; background: rgba(0,0,0,0.4); border-radius: 5px; overflow: hidden;">
            <div class="progress-bar-fill" style="width: {pct}%; height: 100%; 
                background: linear-gradient(90deg, {color1}, {color2}); border-radius: 5px;">
            </div>
        </div>
        {f'<div style="margin-top: 0.5rem; font-size: 0.75rem; color: rgba(255,255,255,0.5); font-family: monospace;">{status_text}</div>' if status_text else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_terminal(logs: List[Dict[str, Any]]):
    """Renderiza la consola de logs estilo terminal."""
    lines_html = ""
    
    for log in logs[:10]:
        timestamp = format_timestamp(log.get('timestamp', ''))
        level = log.get('level', 'INFO').upper()
        message = log.get('message', '')
        
        level_class = f"terminal-level-{level.lower()}" if level.lower() in ['info', 'success', 'warning', 'error'] else 'terminal-level-info'
        
        lines_html += f"""
        <div class="terminal-line">
            <span class="terminal-timestamp">[{timestamp}]</span>
            <span class="{level_class}">[{level}]</span>
            <span style="color: rgba(255,255,255,0.8);">{message}</span>
        </div>
        """
    
    html = f"""
    <div class="terminal-container">
        <div class="terminal-header">
            <div class="terminal-dot red"></div>
            <div class="terminal-dot yellow"></div>
            <div class="terminal-dot green"></div>
            <span class="terminal-title">system_logs — bash — 80×24</span>
        </div>
        <div class="terminal-body">
            {lines_html}
            <div class="terminal-line">
                <span style="color: #00ff88;">➜</span>
                <span style="color: #00d4ff;">~</span>
                <span class="terminal-cursor"></span>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_status_badge(status: str, is_running: bool):
    """Renderiza un badge de estado."""
    if is_running:
        html = """
        <span class="status-indicator status-online">
            <span class="pulse-dot"></span>
            ONLINE
        </span>
        """
    else:
        html = """
        <span class="status-indicator status-offline">
            <span style="width: 8px; height: 8px; border-radius: 50%; background: currentColor;"></span>
            OFFLINE
        </span>
        """
    st.markdown(html, unsafe_allow_html=True)

def render_lottie_animation(animation_type: str, height: int = 200):
    """Renderiza animación Lottie usando lottie-web."""
    # URLs de animaciones de LottieFiles
    animations = {
        "search": "https://assets9.lottiefiles.com/packages/lf20_5w2kxxnj.json",
        "success": "https://assets2.lottiefiles.com/packages/lf20_s2lryxtd.json",
        "loading": "https://assets9.lottiefiles.com/packages/lf20_b88nh30c.json",
        "upload": "https://assets3.lottiefiles.com/packages/lf20_j1adxtyb.json",
        "robot": "https://assets5.lottiefiles.com/packages/lf20_w51pcehl.json",
    }
    
    url = animations.get(animation_type, animations["loading"])
    
    html = f"""
    <div style="display: flex; justify-content: center; align-items: center;">
        <lottie-player
            src="{url}"
            background="transparent"
            speed="1"
            style="width: {height}px; height: {height}px;"
            loop
            autoplay>
        </lottie-player>
    </div>
    <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
    """
    st.components.v1.html(html, height=height)

# ═══════════════════════════════════════════════════════════════════════════════
# INICIALIZACIÓN DE ESTADO DE SESIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def init_session_state():
    """Inicializa variables de estado de sesión."""
    defaults = {
        'last_update': time.time(),
        'logs_history': [],
        'workers_started': False,
        'upload_success': False,
        'current_dni_sunedu': None,
        'current_dni_minedu': None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # Configuración de página
    st.set_page_config(
        page_title="ETL Pipeline | Validador de Grados",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # Inicializar estado
    init_session_state()
    
    # Aplicar CSS personalizado
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown(LOTTIE_CSS, unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HEADER - Título Cyberpunk con animación
    # ═══════════════════════════════════════════════════════════════════════════
    
    col_header_left, col_header_center, col_header_right = st.columns([1, 3, 1])
    
    with col_header_left:
        # Icono animado
        st.markdown(f"""
        <div style="display: flex; justify-content: center; align-items: center; height: 100px;">
            {get_animated_icon('rocket', 70)}
        </div>
        """, unsafe_allow_html=True)
    
    with col_header_center:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h1 class="cyber-title" style="font-size: 2.5rem; margin-bottom: 0.5rem;">
                ⚡ ETL PIPELINE ENGINE ⚡
            </h1>
            <p style="color: rgba(255,255,255,0.5); font-size: 0.9rem; letter-spacing: 0.1em; text-transform: uppercase;">
                Validador de Grados Académicos — SUNEDU → MINEDU
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_header_right:
        # Estado de conexión
        api_status = api_get("/api/status")
        is_connected = api_status is not None
        
        status_color = "#00ff88" if is_connected else "#ff4757"
        status_text = "CONECTADO" if is_connected else "DESCONECTADO"
        
        st.markdown(f"""
        <div style="text-align: center; padding: 1.5rem 0;">
            <div style="display: inline-flex; align-items: center; gap: 0.5rem; 
                        padding: 0.5rem 1rem; background: rgba(0,0,0,0.4); 
                        border-radius: 20px; border: 1px solid {status_color}40;">
                <div style="width: 8px; height: 8px; border-radius: 50%; 
                           background: {status_color}; animation: {'pulse-dot 1.5s infinite' if is_connected else 'none'};"></div>
                <span style="color: {status_color}; font-size: 0.75rem; font-weight: 600;">{status_text}</span>
            </div>
            <div style="color: rgba(255,255,255,0.3); font-size: 0.7rem; margin-top: 0.5rem;">
                API: {API_BASE_URL}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    if not is_connected:
        st.error("""
        ### 🔌 Sin conexión con el backend
        
        No se puede conectar con la API. Por favor:
        1. Verifica que el servidor API esté corriendo: `python api.py`
        2. Verifica la URL en la configuración: `API_BASE_URL = "http://127.0.0.1:8000"`
        """)
        st.stop()
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SIDEBAR - Zona de Control
    # ═══════════════════════════════════════════════════════════════════════════
    
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <h3 style="color: #00d4ff; font-size: 1rem; text-transform: uppercase; letter-spacing: 0.1em;">
                🎛️ Panel de Control
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        # ── Estado de Workers ──
        st.markdown('<div class="glass-container" style="margin-bottom: 1rem;">', unsafe_allow_html=True)
        st.markdown("<h4 style='color: rgba(255,255,255,0.8); font-size: 0.875rem; margin-bottom: 1rem;'>🤖 Estado de Workers</h4>", unsafe_allow_html=True)
        
        workers = api_get("/api/workers/status") or {}
        
        col_w1, col_w2 = st.columns(2)
        
        with col_w1:
            sunedu = workers.get("sunedu", {})
            sunedu_running = sunedu.get("running", False)
            st.markdown("<div style='text-align: center;'><span style='color: rgba(255,255,255,0.6); font-size: 0.75rem;'>SUNEDU</span></div>", unsafe_allow_html=True)
            render_status_badge("sunedu", sunedu_running)
            if sunedu_running and sunedu.get("restart_count", 0) > 0:
                st.caption(f"🔄 {sunedu['restart_count']} reinicios")
        
        with col_w2:
            minedu = workers.get("minedu", {})
            minedu_running = minedu.get("running", False)
            st.markdown("<div style='text-align: center;'><span style='color: rgba(255,255,255,0.6); font-size: 0.75rem;'>MINEDU</span></div>", unsafe_allow_html=True)
            render_status_badge("minedu", minedu_running)
            if minedu_running and minedu.get("restart_count", 0) > 0:
                st.caption(f"🔄 {minedu['restart_count']} reinicios")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # ── Botones de Control ──
        st.markdown("<div style='margin: 1rem 0;'>", unsafe_allow_html=True)
        
        col_start, col_stop = st.columns(2)
        
        with col_start:
            if st.button("▶ INICIAR", use_container_width=True, key="btn_start"):
                with st.spinner("Iniciando workers..."):
                    result = api_post("/api/workers/start")
                    if result:
                        st.session_state.workers_started = True
                        st.success("✅ Workers iniciados")
                        time.sleep(0.5)
                        st.rerun()
        
        with col_stop:
            if st.button("⏹ DETENER", use_container_width=True, key="btn_stop"):
                with st.spinner("Deteniendo workers..."):
                    result = api_post("/api/workers/stop")
                    if result:
                        st.session_state.workers_started = False
                        st.warning("⏹ Workers detenidos")
                        time.sleep(0.5)
                        st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<hr>", unsafe_allow_html=True)
        
        # ── Upload de archivo ──
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        st.markdown("<h4 style='color: rgba(255,255,255,0.8); font-size: 0.875rem; margin-bottom: 1rem;'>📤 Subir DNIs</h4>", unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(
            "",
            type=["xlsx", "xls", "csv"],
            key="file_uploader",
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            file_size = len(uploaded_file.getvalue()) / 1024  # KB
            st.markdown(f"""
            <div style="padding: 0.75rem; background: rgba(0,212,255,0.1); border-radius: 8px; margin: 0.5rem 0;">
                <div style="font-size: 0.8rem; color: #00d4ff;">📄 {uploaded_file.name}</div>
                <div style="font-size: 0.7rem; color: rgba(255,255,255,0.5);">{file_size:.1f} KB</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚀 CARGAR Y PROCESAR", use_container_width=True, type="primary", key="btn_upload"):
                with st.spinner("Procesando archivo..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        r = requests.post(f"{API_BASE_URL}/api/upload", files=files, timeout=60)
                        r.raise_for_status()
                        data = r.json()
                        
                        st.session_state.upload_success = True
                        st.success(f"✅ Lote **#{data['lote_id']}** creado")
                        st.info(f"📊 **{data['total_dnis']}** DNIs cargados")
                        
                        # Auto-iniciar workers si no están corriendo
                        if not (sunedu_running or minedu_running):
                            api_post("/api/workers/start")
                            st.info("🤖 Workers auto-iniciados")
                        
                        time.sleep(1)
                        st.rerun()
                    except requests.HTTPError as e:
                        body = e.response.json() if e.response else {}
                        st.error(f"❌ {body.get('detail', str(e))}")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<hr>", unsafe_allow_html=True)
        
        # ── Auto-refresh Toggle ──
        auto_refresh = st.toggle("🔄 Auto-refresh (2s)", value=True, key="auto_refresh")
        
        if st.button("🔄 Actualizar ahora", use_container_width=True):
            st.rerun()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PANEL PRINCIPAL - Métricas y Progreso
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Obtener datos actuales
    status = api_get("/api/status") or {}
    total = status.get("total", 0)
    terminados = status.get("terminados", 0)
    progreso = status.get("progreso_pct", 0)
    conteos = status.get("conteos", {})
    pipeline = status.get("pipeline", {})
    
    # ── Métricas principales ──
    st.markdown('<div class="glass-container" style="margin-bottom: 1.5rem;">', unsafe_allow_html=True)
    st.markdown("<h3 style='color: rgba(255,255,255,0.9); margin-bottom: 1.5rem; font-size: 1.1rem;'>📊 Métricas en Vivo</h3>", unsafe_allow_html=True)
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        render_metric_card(
            "Total DNIs", 
            total, 
            "#a855f7",  # Purple
            "total"
        )
    
    with col_m2:
        found_sunedu = conteos.get("FOUND_SUNEDU", 0)
        render_metric_card(
            "Encontrados SUNEDU", 
            found_sunedu, 
            "#00ff88",  # Green
            "sunedu"
        )
    
    with col_m3:
        found_minedu = conteos.get("FOUND_MINEDU", 0)
        render_metric_card(
            "Encontrados MINEDU", 
            found_minedu, 
            "#3b82f6",  # Blue
            "minedu"
        )
    
    with col_m4:
        not_found = conteos.get("NOT_FOUND", 0)
        render_metric_card(
            "Sin Títulos", 
            not_found, 
            "#ff4757",  # Red
            "notfound"
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PIPELINE WATERFALL - Barras de progreso por worker
    # ═══════════════════════════════════════════════════════════════════════════
    
    st.markdown('<div class="glass-container" style="margin-bottom: 1.5rem;">', unsafe_allow_html=True)
    st.markdown("<h3 style='color: rgba(255,255,255,0.9); margin-bottom: 1.5rem; font-size: 1.1rem;'>🔄 Pipeline Waterfall</h3>", unsafe_allow_html=True)
    
    col_pipe1, col_pipe2 = st.columns(2)
    
    with col_pipe1:
        # SUNEDU Pipeline
        s = pipeline.get("sunedu", {})
        s_pendientes = s.get("pendientes", 0)
        s_procesando = s.get("procesando", 0)
        s_encontrados = s.get("encontrados", 0)
        s_derivados = s.get("derivados_minedu", 0)
        s_errores = s.get("errores", 0)
        
        s_total = s_pendientes + s_procesando + s_encontrados + s_derivados + s_errores
        s_completados = s_encontrados + s_derivados + s_errores
        
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;">
            <span style="font-size: 1.5rem;">🏛️</span>
            <span style="font-weight: 700; color: #00ff88; font-size: 1.1rem;">SUNEDU Worker</span>
            <span style="background: rgba(0,255,136,0.15); color: #00ff88; padding: 0.2rem 0.5rem; 
                        border-radius: 4px; font-size: 0.7rem; text-transform: uppercase;">Universidades</span>
        </div>
        """, unsafe_allow_html=True)
        
        if s_total > 0:
            render_progress_bar(
                "Progreso SUNEDU",
                s_completados,
                s_total,
                "#00ff88",
                "#00d4ff",
                f"⏳ Pendientes: {s_pendientes} | 🔄 Procesando: {s_procesando} | ✅ Encontrados: {s_encontrados}"
            )
        else:
            st.info("No hay DNIs pendientes en SUNEDU")
        
        # Mini métricas
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; margin-top: 1rem;">
            <div style="text-align: center; padding: 0.5rem; background: rgba(0,0,0,0.3); border-radius: 8px;">
                <div style="font-size: 1.2rem; font-weight: 700; color: #ffbd2e;">{s_pendientes}</div>
                <div style="font-size: 0.65rem; color: rgba(255,255,255,0.5);">PENDIENTES</div>
            </div>
            <div style="text-align: center; padding: 0.5rem; background: rgba(0,0,0,0.3); border-radius: 8px;">
                <div style="font-size: 1.2rem; font-weight: 700; color: #00ff88;">{s_encontrados}</div>
                <div style="font-size: 0.65rem; color: rgba(255,255,255,0.5);">ENCONTRADOS</div>
            </div>
            <div style="text-align: center; padding: 0.5rem; background: rgba(0,0,0,0.3); border-radius: 8px;">
                <div style="font-size: 1.2rem; font-weight: 700; color: #3b82f6;">{s_derivados}</div>
                <div style="font-size: 0.65rem; color: rgba(255,255,255,0.5);">→ MINEDU</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_pipe2:
        # MINEDU Pipeline
        m = pipeline.get("minedu", {})
        m_pendientes = m.get("pendientes", 0)
        m_procesando = m.get("procesando", 0)
        m_encontrados = m.get("encontrados", 0)
        m_no_encontrados = m.get("no_encontrados", 0)
        m_errores = m.get("errores", 0)
        
        m_total = m_pendientes + m_procesando + m_encontrados + m_no_encontrados + m_errores
        m_completados = m_encontrados + m_no_encontrados + m_errores
        
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;">
            <span style="font-size: 1.5rem;">📚</span>
            <span style="font-weight: 700; color: #3b82f6; font-size: 1.1rem;">MINEDU Worker</span>
            <span style="background: rgba(59,130,246,0.15); color: #3b82f6; padding: 0.2rem 0.5rem; 
                        border-radius: 4px; font-size: 0.7rem; text-transform: uppercase;">Institutos</span>
        </div>
        """, unsafe_allow_html=True)
        
        if m_total > 0:
            render_progress_bar(
                "Progreso MINEDU",
                m_completados,
                m_total,
                "#3b82f6",
                "#a855f7",
                f"⏳ Pendientes: {m_pendientes} | 🔄 Procesando: {m_procesando} | ✅ Encontrados: {m_encontrados}"
            )
        else:
            st.info("No hay DNIs derivados a MINEDU aún")
        
        # Mini métricas
        st.markdown(f"""
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; margin-top: 1rem;">
            <div style="text-align: center; padding: 0.5rem; background: rgba(0,0,0,0.3); border-radius: 8px;">
                <div style="font-size: 1.2rem; font-weight: 700; color: #ffbd2e;">{m_pendientes}</div>
                <div style="font-size: 0.65rem; color: rgba(255,255,255,0.5);">PENDIENTES</div>
            </div>
            <div style="text-align: center; padding: 0.5rem; background: rgba(0,0,0,0.3); border-radius: 8px;">
                <div style="font-size: 1.2rem; font-weight: 700; color: #00ff88;">{m_encontrados}</div>
                <div style="font-size: 0.65rem; color: rgba(255,255,255,0.5);">ENCONTRADOS</div>
            </div>
            <div style="text-align: center; padding: 0.5rem; background: rgba(0,0,0,0.3); border-radius: 8px;">
                <div style="font-size: 1.2rem; font-weight: 700; color: #ff4757;">{m_no_encontrados}</div>
                <div style="font-size: 0.65rem; color: rgba(255,255,255,0.5);">NO ENCONTR.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FILA INFERIOR: Terminal de Logs y Tabla de Resultados
    # ═══════════════════════════════════════════════════════════════════════════
    
    col_bottom_left, col_bottom_right = st.columns([1, 2])
    
    with col_bottom_left:
        # Consola de Logs estilo Terminal
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        
        # Generar logs simulados basados en el estado actual
        logs = []
        
        # Logs basados en el procesamiento actual
        if s_procesando > 0 or m_procesando > 0:
            logs.append({"timestamp": datetime.now().isoformat(), "level": "INFO", "message": f"Procesando DNI en SUNEDU..."})
        if s_encontrados > 0:
            logs.append({"timestamp": datetime.now().isoformat(), "level": "SUCCESS", "message": f"Encontrados {s_encontrados} registros en SUNEDU"})
        if m_encontrados > 0:
            logs.append({"timestamp": datetime.now().isoformat(), "level": "SUCCESS", "message": f"Encontrados {m_encontrados} registros en MINEDU"})
        if s_derivados > 0:
            logs.append({"timestamp": datetime.now().isoformat(), "level": "INFO", "message": f"{s_derivados} DNIs derivados a MINEDU"})
        
        # Logs de sistema
        logs.extend([
            {"timestamp": datetime.now().isoformat(), "level": "INFO", "message": f"Total DNIs en sistema: {total}"},
            {"timestamp": datetime.now().isoformat(), "level": "INFO", "message": f"Progreso general: {progreso:.1f}%"},
        ])
        
        if s_errores > 0 or m_errores > 0:
            logs.append({"timestamp": datetime.now().isoformat(), "level": "WARNING", "message": f"Errores detectados: SUNEDU({s_errores}) MINEDU({m_errores})"})
        
        render_terminal(logs)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col_bottom_right:
        # Tabla de Resultados
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        st.markdown("<h3 style='color: rgba(255,255,255,0.9); margin-bottom: 1rem; font-size: 1.1rem;'>📋 Resultados Recientes</h3>", unsafe_allow_html=True)
        
        # Tabs para filtrar
        tab_all, tab_sunedu, tab_minedu, tab_notfound = st.tabs(["Todos", "SUNEDU ✅", "MINEDU ✅", "No encontrados"])
        
        with tab_all:
            registros = api_get("/api/registros?limit=50") or []
            if registros:
                df = pd.DataFrame(registros)
                cols_show = ["dni", "estado", "updated_at"]
                cols_present = [c for c in cols_show if c in df.columns]
                
                # Añadir info de payloads si existe
                for c in ["sunedu_nombres", "sunedu_grado", "minedu_titulo"]:
                    if c in df.columns:
                        cols_present.append(c)
                
                st.dataframe(
                    df[cols_present].head(20),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "dni": st.column_config.TextColumn("DNI", width="small"),
                        "estado": st.column_config.TextColumn("Estado", width="medium"),
                        "updated_at": st.column_config.DatetimeColumn("Última actualización", width="medium"),
                    }
                )
            else:
                st.info("No hay registros para mostrar")
        
        with tab_sunedu:
            registros = api_get("/api/registros?estado=FOUND_SUNEDU&limit=50") or []
            if registros:
                df = pd.DataFrame(registros)
                st.dataframe(df.head(20), use_container_width=True, hide_index=True)
            else:
                st.info("Sin registros de SUNEDU")
        
        with tab_minedu:
            registros = api_get("/api/registros?estado=FOUND_MINEDU&limit=50") or []
            if registros:
                df = pd.DataFrame(registros)
                st.dataframe(df.head(20), use_container_width=True, hide_index=True)
            else:
                st.info("Sin registros de MINEDU")
        
        with tab_notfound:
            registros = api_get("/api/registros?estado=NOT_FOUND&limit=50") or []
            if registros:
                df = pd.DataFrame(registros)
                st.dataframe(df.head(20), use_container_width=True, hide_index=True)
            else:
                st.info("Sin registros no encontrados")
        
        # Botón de descarga
        col_dl, _ = st.columns([1, 3])
        with col_dl:
            if st.button("📥 Descargar Excel", use_container_width=True, type="primary"):
                try:
                    r = requests.get(f"{API_BASE_URL}/api/resultados", timeout=60)
                    r.raise_for_status()
                    
                    st.download_button(
                        label="💾 Guardar archivo",
                        data=r.content,
                        file_name=f"resultados_validacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                except Exception as e:
                    st.error(f"Error descargando: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # AUTO-REFRESH (Polling cada 2 segundos)
    # ═══════════════════════════════════════════════════════════════════════════
    
    if auto_refresh and (s_procesando > 0 or m_procesando > 0 or s_pendientes > 0 or m_pendientes > 0):
        time.sleep(POLL_INTERVAL)
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()

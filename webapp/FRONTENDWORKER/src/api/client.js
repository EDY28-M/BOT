/**
 * API Client — centralised HTTP calls to FastAPI backend.
 * Each browser tab gets a unique session UUID.
 * In dev, Vite proxy forwards /api → http://127.0.0.1:8000
 */

const BASE = ''  // same origin

// ─── Session Management ───

function uuidv4() {
  return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, c =>
    (+c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> +c / 4).toString(16)
  );
}

// Fallback simple si crypto no está disponible (HTTP local)
function simpleUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

function getSessionId() {
  let sid = localStorage.getItem('SICGT_session_id')
  if (!sid) {
    // Usar crypto si existe, sino fallback
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      sid = crypto.randomUUID();
    } else {
      sid = simpleUUID();
    }
    localStorage.setItem('SICGT_session_id', sid)
  }
  return sid
}

const SESSION_ID = getSessionId()

// ─── HTTP Helpers ───

async function request(url, options = {}) {
  const headers = {
    'X-Session-ID': SESSION_ID,
    ...(options.headers || {}),
  }
  const res = await fetch(`${BASE}${url}`, { ...options, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `HTTP ${res.status}`)
  }
  return res
}

async function json(url, options) {
  const res = await request(url, options)
  return res.json()
}

// ─── Endpoints ───

export async function fetchStatus() {
  return json('/api/status')
}

export async function fetchWorkersStatus() {
  return json('/api/workers/status')
}

export async function fetchRegistros(params = {}) {
  const q = new URLSearchParams()
  if (params.estado) q.set('estado', params.estado)
  if (params.lote_id) q.set('lote_id', params.lote_id)
  q.set('limit', String(params.limit || 200))
  q.set('offset', String(params.offset || 0))
  return json(`/api/registros?${q}`)
}

export async function fetchLotes() {
  return json('/api/lotes')
}

export async function uploadFile(file) {
  const fd = new FormData()
  fd.append('file', file)
  // FormData sets its own Content-Type, don't override
  return json('/api/upload', { method: 'POST', body: fd })
}

export async function startWorkers() {
  return json('/api/workers/start', { method: 'POST' })
}

export async function stopWorkers() {
  return json('/api/workers/stop', { method: 'POST' })
}

export async function clearAll() {
  return json('/api/limpiar', { method: 'POST' })
}

export async function retryNotFound() {
  return json('/api/retry', { method: 'POST' })
}

export async function recoverStuck() {
  return json('/api/recover', { method: 'POST' })
}

export async function downloadResultados() {
  const res = await request('/api/resultados')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'resultados_SICGT.xlsx'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export function getActiveSessionId() {
  return SESSION_ID
}

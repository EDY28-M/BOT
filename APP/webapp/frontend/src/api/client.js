/**
 * API Client — centralised HTTP calls to FastAPI backend.
 * In dev, Vite proxy forwards /api → http://127.0.0.1:8000
 * In prod, same origin (served by FastAPI).
 */

const BASE = ''  // same origin

async function request(url, options = {}) {
  const res = await fetch(`${BASE}${url}`, options)
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

export async function downloadResultados() {
  const res = await request('/api/resultados')
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'resultados_validacion.xlsx'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

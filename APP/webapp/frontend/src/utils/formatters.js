/** Number & percentage helpers */

export function fmt(n) {
  return n != null ? n.toLocaleString('en-US') : '0'
}

export function pct(part, total) {
  return total > 0 ? (part / total * 100).toFixed(1) : '0.0'
}

export function ts() {
  return new Date().toLocaleTimeString('es-PE', { hour12: false })
}

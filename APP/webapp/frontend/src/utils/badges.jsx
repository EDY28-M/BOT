/** Badge & status icon renderers (return JSX-compatible strings for dangerouslySetInnerHTML or React elements) */
import React from 'react'

export function SourceBadge({ estado }) {
  if (estado === 'FOUND_SUNEDU' || estado === 'PROCESANDO_SUNEDU')
    return (
      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-neon-green/10 text-neon-green border border-neon-green/20">
        SUNEDU
      </span>
    )
  if (estado === 'FOUND_MINEDU' || estado === 'PROCESANDO_MINEDU' || estado === 'CHECK_MINEDU')
    return (
      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-neon-blue/10 text-neon-blue border border-neon-blue/20">
        MINEDU
      </span>
    )
  if (estado === 'NOT_FOUND')
    return (
      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
        ---
      </span>
    )
  if (estado?.startsWith('ERROR'))
    return (
      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-neon-red/10 text-neon-red border border-neon-red/20">
        ERROR
      </span>
    )
  return (
    <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
      {estado || '—'}
    </span>
  )
}

export function StatusIcon({ estado }) {
  if (estado === 'FOUND_SUNEDU' || estado === 'FOUND_MINEDU')
    return <span className="text-neon-green material-icons-round text-sm">check_circle</span>
  if (estado === 'NOT_FOUND')
    return <span className="text-neon-red material-icons-round text-sm">cancel</span>
  if (estado?.startsWith('ERROR'))
    return <span className="text-yellow-500 material-icons-round text-sm">warning</span>
  if (estado?.startsWith('PROCESANDO'))
    return <span className="text-neon-blue material-icons-round text-sm animate-spin">sync</span>
  return <span className="text-slate-500 material-icons-round text-sm">hourglass_empty</span>
}

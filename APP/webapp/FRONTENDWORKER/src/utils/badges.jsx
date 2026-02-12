/** Badge & status icon renderers for light theme */
import React from 'react'

export function SourceBadge({ estado }) {
  if (estado === 'FOUND_SUNEDU' || estado === 'PROCESANDO_SUNEDU')
    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700 border border-green-200">
        SUNEDU
      </span>
    )
  if (estado === 'FOUND_MINEDU' || estado === 'PROCESANDO_MINEDU' || estado === 'CHECK_MINEDU')
    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700 border border-blue-200">
        MINEDU
      </span>
    )
  if (estado === 'NOT_FOUND')
    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
        ---
      </span>
    )
  if (estado?.startsWith('ERROR'))
    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-600 border border-red-200">
        ERROR
      </span>
    )
  return (
    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
      {estado || '—'}
    </span>
  )
}

export function StatusIcon({ estado }) {
  if (estado === 'FOUND_SUNEDU' || estado === 'FOUND_MINEDU')
    return <span className="text-green-500 material-icons-round text-sm">check_circle</span>
  if (estado === 'NOT_FOUND')
    return <span className="text-red-400 material-icons-round text-sm">cancel</span>
  if (estado?.startsWith('ERROR'))
    return <span className="text-amber-500 material-icons-round text-sm">warning</span>
  if (estado?.startsWith('PROCESANDO'))
    return <span className="text-blue-500 material-icons-round text-sm animate-spin">sync</span>
  return <span className="text-gray-300 material-icons-round text-sm">hourglass_empty</span>
}

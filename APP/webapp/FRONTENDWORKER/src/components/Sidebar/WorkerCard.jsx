import React, { memo } from 'react'

const STYLES = {
  sunedu: {
    icon: 'school',
    label: 'SUNEDU',
    active: {
      card: 'p-3 rounded-lg border border-green-200 bg-green-50 flex items-center justify-between transition-all',
      icon: 'material-icons-round text-green-600',
      status: 'text-xs text-green-600 font-medium',
      dot: 'h-3 w-3 rounded-full bg-green-500 animate-pulse',
    },
    inactive: {
      card: 'p-3 rounded-lg border border-gray-200 bg-gray-50 flex items-center justify-between transition-all',
      icon: 'material-icons-round text-gray-400',
      status: 'text-xs text-gray-400',
      dot: 'h-3 w-3 rounded-full bg-gray-300',
    },
  },
  minedu: {
    icon: 'account_balance',
    label: 'MINEDU',
    active: {
      card: 'p-3 rounded-lg border border-blue-200 bg-blue-50 flex items-center justify-between transition-all',
      icon: 'material-icons-round text-blue-600',
      status: 'text-xs text-blue-600 font-medium',
      dot: 'h-3 w-3 rounded-full bg-blue-500 animate-pulse',
    },
    inactive: {
      card: 'p-3 rounded-lg border border-gray-200 bg-gray-50 flex items-center justify-between transition-all',
      icon: 'material-icons-round text-gray-400',
      status: 'text-xs text-gray-400',
      dot: 'h-3 w-3 rounded-full bg-gray-300',
    },
  },
}

function WorkerCard({ name, running }) {
  const cfg = STYLES[name]
  const s = running ? cfg.active : cfg.inactive

  return (
    <div className={s.card}>
      <div className="flex items-center gap-3">
        <span className={s.icon}>{cfg.icon}</span>
        <div>
          <p className="text-sm font-bold text-gray-800">{cfg.label}</p>
          <p className={s.status}>{running ? 'Procesando…' : 'Detenido'}</p>
        </div>
      </div>
      <div className={s.dot} />
    </div>
  )
}

export default memo(WorkerCard)

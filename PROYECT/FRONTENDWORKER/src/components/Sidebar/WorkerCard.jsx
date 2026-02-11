import React, { memo } from 'react'

const STYLES = {
  sunedu: {
    icon: 'school',
    label: 'SUNEDU Node',
    active: {
      card: 'p-3 rounded-lg border border-neon-green/30 bg-neon-green/5 flex items-center justify-between transition-all',
      icon: 'material-icons-round text-neon-green',
      status: 'text-xs text-neon-green',
      dot: 'h-3 w-3 rounded-full bg-neon-green animate-pulse-green',
    },
    inactive: {
      card: 'p-3 rounded-lg border border-slate-700 bg-slate-800/30 flex items-center justify-between transition-all',
      icon: 'material-icons-round text-slate-500',
      status: 'text-xs text-slate-500',
      dot: 'h-3 w-3 rounded-full bg-slate-600',
    },
  },
  minedu: {
    icon: 'account_balance',
    label: 'MINEDU Node',
    active: {
      card: 'p-3 rounded-lg border border-neon-blue/30 bg-neon-blue/5 flex items-center justify-between transition-all',
      icon: 'material-icons-round text-neon-blue',
      status: 'text-xs text-neon-blue',
      dot: 'h-3 w-3 rounded-full bg-neon-blue animate-pulse-blue',
    },
    inactive: {
      card: 'p-3 rounded-lg border border-slate-700 bg-slate-800/30 flex items-center justify-between transition-all',
      icon: 'material-icons-round text-slate-500',
      status: 'text-xs text-slate-500',
      dot: 'h-3 w-3 rounded-full bg-slate-600',
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
          <p className="text-sm font-bold text-white">{cfg.label}</p>
          <p className={s.status}>{running ? 'Scraping Active' : 'Stopped'}</p>
        </div>
      </div>
      <div className={s.dot} />
    </div>
  )
}

export default memo(WorkerCard)

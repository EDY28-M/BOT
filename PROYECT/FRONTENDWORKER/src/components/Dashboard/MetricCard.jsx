import React, { memo } from 'react'

const STYLES = {
  primary: {
    border: 'glass-panel p-5 rounded-xl border-l-4 border-l-primary relative overflow-hidden group',
    icon: 'material-icons-round text-6xl text-primary',
    sub: 'mt-2 text-xs text-primary font-mono flex items-center gap-1',
  },
  green: {
    border: 'glass-panel p-5 rounded-xl border-l-4 border-l-neon-green relative overflow-hidden group',
    icon: 'material-icons-round text-6xl text-neon-green',
    sub: 'mt-2 text-xs text-neon-green font-mono flex items-center gap-1',
  },
  blue: {
    border: 'glass-panel p-5 rounded-xl border-l-4 border-l-neon-blue relative overflow-hidden group',
    icon: 'material-icons-round text-6xl text-neon-blue',
    sub: 'mt-2 text-xs text-neon-blue font-mono flex items-center gap-1',
  },
  red: {
    border: 'glass-panel p-5 rounded-xl border-l-4 border-l-neon-red relative overflow-hidden group',
    icon: 'material-icons-round text-6xl text-neon-red',
    sub: 'mt-2 text-xs text-neon-red font-mono flex items-center gap-1',
  },
}

function MetricCard({ label, value, sub, icon, color = 'primary' }) {
  const s = STYLES[color]
  return (
    <div className={s.border}>
      <div className="absolute right-0 top-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
        <span className={s.icon}>{icon}</span>
      </div>
      <p className="text-slate-400 text-sm font-medium uppercase tracking-wider">{label}</p>
      <h2 className="text-4xl font-bold text-white mt-1 group-hover:scale-105 transition-transform origin-left">
        {value}
      </h2>
      <div className={s.sub}>
        {sub}
      </div>
    </div>
  )
}

export default memo(MetricCard)

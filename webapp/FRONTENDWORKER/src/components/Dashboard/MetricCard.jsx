import React, { memo } from 'react'

const STYLES = {
  primary: {
    border: 'card-panel p-5 rounded-xl border-l-4 border-l-primary relative overflow-hidden group',
    icon: 'material-icons-round text-6xl text-primary/20',
    sub: 'mt-2 text-xs text-primary font-mono flex items-center gap-1',
  },
  green: {
    border: 'card-panel p-5 rounded-xl border-l-4 border-l-green-500 relative overflow-hidden group',
    icon: 'material-icons-round text-6xl text-green-500/20',
    sub: 'mt-2 text-xs text-green-600 font-mono flex items-center gap-1',
  },
  blue: {
    border: 'card-panel p-5 rounded-xl border-l-4 border-l-blue-500 relative overflow-hidden group',
    icon: 'material-icons-round text-6xl text-blue-500/20',
    sub: 'mt-2 text-xs text-blue-600 font-mono flex items-center gap-1',
  },
  red: {
    border: 'card-panel p-5 rounded-xl border-l-4 border-l-red-500 relative overflow-hidden group',
    icon: 'material-icons-round text-6xl text-red-500/20',
    sub: 'mt-2 text-xs text-red-500 font-mono flex items-center gap-1',
  },
}

function MetricCard({ label, value, sub, icon, color = 'primary' }) {
  const s = STYLES[color]
  return (
    <div className={s.border}>
      <div className="absolute right-0 top-0 p-4">
        <span className={s.icon}>{icon}</span>
      </div>
      <p className="text-gray-500 text-sm font-medium uppercase tracking-wider">{label}</p>
      <h2 className="text-4xl font-bold text-gray-900 mt-1 group-hover:scale-105 transition-transform origin-left">
        {value}
      </h2>
      <div className={s.sub}>
        {sub}
      </div>
    </div>
  )
}

export default memo(MetricCard)

import React, { memo } from 'react'
import { useDashboard } from '../../context/DashboardContext'

const TABS = [
  { key: 'all', label: 'All Records' },
  { key: 'sunedu', label: 'SUNEDU', countKey: 'FOUND_SUNEDU', badgeCls: 'bg-neon-green/20 text-neon-green' },
  { key: 'minedu', label: 'MINEDU', countKey: 'FOUND_MINEDU', badgeCls: 'bg-neon-blue/20 text-neon-blue' },
  { key: 'notfound', label: 'Not Found', countKey: 'NOT_FOUND', badgeCls: 'bg-neon-red/20 text-neon-red' },
  { key: 'errors', label: 'Errors', countKey: null, badgeCls: 'bg-yellow-500/20 text-yellow-500' },
]

function TabBar() {
  const { state, dispatch } = useDashboard()
  const { currentTab, conteos } = state

  const errCount = (conteos.ERROR_SUNEDU || 0) + (conteos.ERROR_MINEDU || 0)

  return (
    <div className="px-4 border-b border-primary/20 flex items-center gap-1 overflow-x-auto shrink-0">
      {TABS.map(tab => {
        const active = currentTab === tab.key
        const count = tab.key === 'errors' ? errCount : (tab.countKey ? conteos[tab.countKey] || 0 : null)

        return (
          <button
            key={tab.key}
            onClick={() => dispatch({ type: 'SET_TAB', payload: tab.key })}
            className={`py-3 px-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
              active
                ? 'text-white border-primary'
                : 'text-slate-400 hover:text-white border-transparent hover:border-slate-600'
            }`}
          >
            {tab.label}
            {count != null && count > 0 && (
              <span className={`${tab.badgeCls} text-[10px] px-1.5 py-0.5 rounded ml-1.5`}>
                {count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

export default memo(TabBar)

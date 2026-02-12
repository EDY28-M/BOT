import React, { memo } from 'react'
import { useDashboard } from '../../context/DashboardContext'

const TABS = [
  { key: 'all', label: 'Todos' },
  { key: 'sunedu', label: 'SUNEDU', countKey: 'FOUND_SUNEDU', badgeCls: 'bg-green-100 text-green-700' },
  { key: 'minedu', label: 'MINEDU', countKey: 'FOUND_MINEDU', badgeCls: 'bg-blue-100 text-blue-700' },
  { key: 'notfound', label: 'No Encontrados', countKey: 'NOT_FOUND', badgeCls: 'bg-red-100 text-red-600' },
  { key: 'errors', label: 'Errores', countKey: null, badgeCls: 'bg-amber-100 text-amber-700' },
]

function TabBar() {
  const { state, dispatch } = useDashboard()
  const { currentTab, conteos } = state

  const errCount = (conteos.ERROR_SUNEDU || 0) + (conteos.ERROR_MINEDU || 0)

  return (
    <div className="px-4 border-b border-gray-200 flex items-center gap-1 overflow-x-auto shrink-0 bg-gray-50">
      {TABS.map(tab => {
        const active = currentTab === tab.key
        const count = tab.key === 'errors' ? errCount : (tab.countKey ? conteos[tab.countKey] || 0 : null)

        return (
          <button
            key={tab.key}
            onClick={() => dispatch({ type: 'SET_TAB', payload: tab.key })}
            className={`py-3 px-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${active
                ? 'text-primary border-primary'
                : 'text-gray-400 hover:text-gray-700 border-transparent hover:border-gray-300'
              }`}
          >
            {tab.label}
            {count != null && count > 0 && (
              <span className={`${tab.badgeCls} text-[10px] px-1.5 py-0.5 rounded-full ml-1.5 font-bold`}>
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

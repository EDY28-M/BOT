import React, { memo, useRef, useEffect } from 'react'
import { useDashboard } from '../../context/DashboardContext'

function Terminal() {
  const { state } = useDashboard()
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [state.logs])

  return (
    <div className="lg:w-1/3 card-panel rounded-xl flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex justify-between items-center shrink-0">
        <span className="text-xs font-medium text-gray-500 flex items-center gap-2">
          <span className="material-icons-round text-sm text-primary">terminal</span>
          Registro de Actividad
        </span>
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
          <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
          <div className="w-2.5 h-2.5 rounded-full bg-green-400" />
        </div>
      </div>

      {/* Logs */}
      <div
        ref={scrollRef}
        className="flex-1 p-4 overflow-y-auto font-mono text-xs space-y-1.5 bg-gray-900"
      >
        {state.logs.map((log, i) => (
          <p key={i} className={log.color || 'text-gray-400'}>
            [{log.time}] {log.msg}
          </p>
        ))}
        <p className="text-green-400 animate-blink">_</p>
      </div>
    </div>
  )
}

export default memo(Terminal)

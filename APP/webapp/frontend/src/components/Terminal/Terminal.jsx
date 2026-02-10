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
    <div className="lg:w-1/3 glass-panel rounded-xl border border-primary/20 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-primary/20 bg-primary/5 flex justify-between items-center shrink-0">
        <span className="text-xs font-mono text-slate-300 flex items-center gap-2">
          <span className="material-icons-round text-sm">terminal</span>
          TERMINAL_OUTPUT
        </span>
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-neon-red" />
          <div className="w-2.5 h-2.5 rounded-full bg-yellow-500" />
          <div className="w-2.5 h-2.5 rounded-full bg-neon-green" />
        </div>
      </div>

      {/* Logs */}
      <div
        ref={scrollRef}
        className="flex-1 p-4 overflow-y-auto font-mono text-xs space-y-1.5 bg-black/40"
      >
        {state.logs.map((log, i) => (
          <p key={i} className={log.color}>
            [{log.time}] {log.msg}
          </p>
        ))}
        <p className="text-neon-green animate-blink">_</p>
      </div>
    </div>
  )
}

export default memo(Terminal)

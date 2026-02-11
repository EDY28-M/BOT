import React, { memo } from 'react'
import { useDashboard } from '../../context/DashboardContext'
import WorkerCard from './WorkerCard'
import FileUpload from './FileUpload'
import Controls from './Controls'

function Sidebar() {
  const { state } = useDashboard()
  const { workers } = state

  return (
    <aside className="w-80 glass-panel border-r border-primary/20 flex flex-col justify-between shrink-0 z-20 relative">
      <div className="p-6">
        {/* Branding */}
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded bg-primary flex items-center justify-center shadow-neon-primary text-white">
            <span className="material-icons-round text-2xl">verified_user</span>
          </div>
          <div>
            <h1 className="font-bold text-lg leading-tight tracking-wider text-white">
              VALIDADOR <span className="text-primary">PRO</span>
            </h1>
            <p className="text-xs text-slate-400 font-mono tracking-widest">v3.0.0 // PIPELINE</p>
          </div>
        </div>

        {/* Worker Status */}
        <div className="space-y-3 mb-8">
          <h3 className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-2">System Status</h3>
          <WorkerCard name="sunedu" running={workers.sunedu?.running} />
          <WorkerCard name="minedu" running={workers.minedu?.running} />
        </div>

        {/* File Upload */}
        <FileUpload />

        {/* Controls */}
        <Controls />
      </div>

      <div className="p-4 border-t border-slate-800 text-center">
        <p className="text-[10px] text-slate-600 font-mono">SECURE CONNECTION // TLS 1.3</p>
      </div>
    </aside>
  )
}

export default memo(Sidebar)

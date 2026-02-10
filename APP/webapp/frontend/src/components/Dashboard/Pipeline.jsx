import React, { memo, useMemo } from 'react'
import { useDashboard } from '../../context/DashboardContext'

function PipelineBar({ label, color, processed, total, shadow }) {
  const width = total > 0 ? Math.min((processed / total) * 100, 100) : 0

  return (
    <div>
      <div className="flex justify-between text-xs font-mono mb-1">
        <span className={`${color} font-bold`}>{label}</span>
        <span className="text-slate-300">
          {processed}/{total} processed
        </span>
      </div>
      <div className="h-3 w-full bg-slate-800 rounded-full overflow-hidden relative">
        <div
          className={`h-full ${color.replace('text-', 'bg-')} progress-striped ${shadow} rounded-full transition-all duration-500`}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  )
}

function Pipeline() {
  const { state } = useDashboard()
  const { pipeline, total } = state
  const sp = pipeline.sunedu || {}
  const mp = pipeline.minedu || {}

  const suneduDone = useMemo(
    () => (sp.encontrados || 0) + (sp.derivados_minedu || 0) + (sp.errores || 0),
    [sp]
  )
  const mineduDone = useMemo(
    () => (mp.encontrados || 0) + (mp.no_encontrados || 0) + (mp.errores || 0),
    [mp]
  )

  const suneduTotal = useMemo(
    () => suneduDone + (sp.procesando || 0) + (sp.pendientes || 0),
    [suneduDone, sp]
  )
  const mineduTotal = useMemo(
    () => mineduDone + (mp.procesando || 0) + (mp.pendientes || 0),
    [mineduDone, mp]
  )

  return (
    <div className="glass-panel p-6 rounded-xl border border-primary/20">
      <div className="flex justify-between items-end mb-4">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
          <span className="material-icons-round text-primary">waterfall_chart</span>
          Waterfall Pipeline
        </h3>
        <span className="font-mono text-xs text-slate-400">
          TOTAL: {total}
        </span>
      </div>

      <div className="space-y-6">
        <PipelineBar
          label="THREAD_A::SUNEDU"
          color="text-neon-green"
          processed={suneduDone}
          total={suneduTotal}
          shadow="shadow-neon-green"
        />
        <PipelineBar
          label="THREAD_B::MINEDU"
          color="text-neon-blue"
          processed={mineduDone}
          total={mineduTotal}
          shadow="shadow-neon-blue"
        />
      </div>
    </div>
  )
}

export default memo(Pipeline)

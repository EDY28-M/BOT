import React, { memo, useMemo } from 'react'
import { useDashboard } from '../../context/DashboardContext'

function PipelineBar({ label, color, bgColor, processed, total }) {
  const width = total > 0 ? Math.min((processed / total) * 100, 100) : 0

  return (
    <div>
      <div className="flex justify-between text-xs font-medium mb-1">
        <span className={`${color} font-bold`}>{label}</span>
        <span className="text-gray-500">
          {processed}/{total} procesados
        </span>
      </div>
      <div className="h-3 w-full bg-gray-100 rounded-full overflow-hidden relative">
        <div
          className={`h-full ${bgColor} progress-striped rounded-full transition-all duration-500`}
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
    <div className="card-panel p-6 rounded-xl">
      <div className="flex justify-between items-end mb-4">
        <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
          <span className="material-icons-round text-primary">waterfall_chart</span>
          Pipeline de Procesamiento
        </h3>
        <span className="font-mono text-xs text-gray-400">
          TOTAL: {total}
        </span>
      </div>

      <div className="space-y-6">
        <PipelineBar
          label="SUNEDU"
          color="text-green-600"
          bgColor="bg-green-500"
          processed={suneduDone}
          total={suneduTotal}
        />
        <PipelineBar
          label="MINEDU"
          color="text-blue-600"
          bgColor="bg-blue-500"
          processed={mineduDone}
          total={mineduTotal}
        />
      </div>
    </div>
  )
}

export default memo(Pipeline)

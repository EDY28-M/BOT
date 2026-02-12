import React, { memo } from 'react'
import { useDashboard } from '../../context/DashboardContext'
import MetricCard from './MetricCard'
import { fmt, pct } from '../../utils/formatters'

function MetricsGrid() {
  const { state } = useDashboard()
  const { total, conteos, progreso_pct } = state
  const fs = conteos.FOUND_SUNEDU || 0
  const fm = conteos.FOUND_MINEDU || 0
  const nf = conteos.NOT_FOUND || 0

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard
        label="Total Procesados"
        value={fmt(total)}
        icon="analytics"
        color="primary"
        sub={
          <>
            <span className="material-icons-round text-[10px]">arrow_upward</span>
            {total > 0 ? `${progreso_pct.toFixed(1)}% completado` : 'Sin datos'}
          </>
        }
      />
      <MetricCard
        label="Encontrados SUNEDU"
        value={fmt(fs)}
        icon="check_circle"
        color="green"
        sub={
          <>
            <span className="material-icons-round text-[10px]">verified</span>
            {total > 0 ? `${pct(fs, total)}% válidos` : '—'}
          </>
        }
      />
      <MetricCard
        label="Encontrados MINEDU"
        value={fmt(fm)}
        icon="fact_check"
        color="blue"
        sub={
          <>
            <span className="material-icons-round text-[10px]">verified</span>
            {total > 0 ? `${pct(fm, total)}% válidos` : '—'}
          </>
        }
      />
      <MetricCard
        label="No Encontrados"
        value={fmt(nf)}
        icon="error_outline"
        color="red"
        sub={
          <>
            <span className="material-icons-round text-[10px]">warning</span>
            {total > 0 ? `${pct(nf, total)}% sin registro` : '—'}
          </>
        }
      />
    </div>
  )
}

export default memo(MetricsGrid)

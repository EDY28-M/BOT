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
        label="Total Processed"
        value={fmt(total)}
        icon="analytics"
        color="primary"
        sub={
          <>
            <span className="material-icons-round text-[10px]">arrow_upward</span>
            {total > 0 ? `${progreso_pct.toFixed(1)}% done` : 'No data'}
          </>
        }
      />
      <MetricCard
        label="Found SUNEDU"
        value={fmt(fs)}
        icon="check_circle"
        color="green"
        sub={
          <>
            <span className="material-icons-round text-[10px]">verified</span>
            {total > 0 ? `${pct(fs, total)}% Valid` : '—'}
          </>
        }
      />
      <MetricCard
        label="Found MINEDU"
        value={fmt(fm)}
        icon="fact_check"
        color="blue"
        sub={
          <>
            <span className="material-icons-round text-[10px]">verified</span>
            {total > 0 ? `${pct(fm, total)}% Valid` : '—'}
          </>
        }
      />
      <MetricCard
        label="Not Found"
        value={fmt(nf)}
        icon="error_outline"
        color="red"
        sub={
          <>
            <span className="material-icons-round text-[10px]">warning</span>
            {total > 0 ? `${pct(nf, total)}% Invalid` : '—'}
          </>
        }
      />
    </div>
  )
}

export default memo(MetricsGrid)

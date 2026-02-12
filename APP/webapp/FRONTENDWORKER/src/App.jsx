import React, { useCallback, useRef } from 'react'
import { DashboardProvider, useDashboard } from './context/DashboardContext'
import usePolling from './hooks/usePolling'
import { fetchStatus, fetchWorkersStatus, fetchRegistros } from './api/client'
import { fmt, ts } from './utils/formatters'

import Sidebar from './components/Sidebar/Sidebar'
import MetricsGrid from './components/Dashboard/MetricsGrid'
import Pipeline from './components/Dashboard/Pipeline'
import Terminal from './components/Terminal/Terminal'
import DataTable from './components/DataTable/DataTable'
import ToastContainer from './components/Toast/ToastContainer'

/** Tab key → API filter(s) */
const TAB_FILTERS = {
  all: {},
  sunedu: { estado: 'FOUND_SUNEDU' },
  minedu: { estado: 'FOUND_MINEDU' },
  notfound: { estado: 'NOT_FOUND' },
  errors: null, // special handling
}

function DashboardContent() {
  const { state, dispatch, addLog } = useDashboard()
  const prev = useRef({
    sRun: false, mRun: false,
    total: 0,
    foundSunedu: 0, derivMinedu: 0,
    foundMinedu: 0, notFound: 0,
    enProceso: 0,
  })

  const poll = useCallback(async () => {
    try {
      const [status, workers] = await Promise.all([
        fetchStatus(),
        fetchWorkersStatus(),
      ])

      dispatch({
        type: 'SET_STATUS',
        payload: {
          total: status.total || 0,
          terminados: status.terminados || 0,
          en_proceso: status.en_proceso || 0,
          progreso_pct: status.progreso_pct || 0,
          conteos: status.conteos || {},
          pipeline: status.pipeline || { sunedu: {}, minedu: {} },
          retry: status.retry || { retryables: 0, pipeline_idle: false, can_retry: false },
        },
      })

      dispatch({ type: 'SET_WORKERS', payload: workers })
      buildLogs(status, workers)
      await fetchRecordsForTab(state.currentTab)
    } catch {
      // silently ignore poll failures
    }
  }, [state.currentTab])

  const buildLogs = useCallback((status, workers) => {
    const p = prev.current
    const sp = status.pipeline?.sunedu || {}
    const mp = status.pipeline?.minedu || {}
    const sRun = !!workers.sunedu?.running
    const mRun = !!workers.minedu?.running

    if (sRun && !p.sRun) addLog('[INFO] Worker SUNEDU conectado.', 'text-blue-600')
    if (!sRun && p.sRun) addLog('[INFO] Worker SUNEDU detenido.', 'text-amber-600')
    if (mRun && !p.mRun) addLog('[INFO] Worker MINEDU conectado.', 'text-blue-600')
    if (!mRun && p.mRun) addLog('[INFO] Worker MINEDU detenido.', 'text-amber-600')

    const total = status.total || 0
    if (total > 0 && total !== p.total)
      addLog(`Cargados ${fmt(total)} registros.`, 'text-gray-500')

    const foundSunedu = sp.encontrados || 0
    if (foundSunedu > p.foundSunedu)
      addLog(`[ENCONTRADO] ${fmt(foundSunedu)} registros — SUNEDU.`, 'text-green-600')

    const derivMinedu = sp.derivados_minedu || 0
    if (derivMinedu > p.derivMinedu)
      addLog(`[DERIVADO] ${fmt(derivMinedu)} DNIs derivados a MINEDU.`, 'text-amber-600')

    const foundMinedu = mp.encontrados || 0
    if (foundMinedu > p.foundMinedu)
      addLog(`[ENCONTRADO] ${fmt(foundMinedu)} registros — MINEDU.`, 'text-green-600')

    const notFound = mp.no_encontrados || 0
    if (notFound > p.notFound)
      addLog(`[NO ENCONTRADO] ${fmt(notFound)} DNIs — Sin registros.`, 'text-red-500')

    const enProceso = status.en_proceso || 0
    if (p.enProceso > 0 && enProceso === 0 && total > 0 && status.terminados === total)
      addLog('[COMPLETADO] Pipeline finalizado.', 'text-green-600')

    prev.current = { sRun, mRun, total, foundSunedu, derivMinedu, foundMinedu, notFound, enProceso }
  }, [addLog])

  const fetchRecordsForTab = useCallback(async (tab) => {
    try {
      let records = []
      if (tab === 'errors') {
        const [se, me] = await Promise.all([
          fetchRegistros({ estado: 'ERROR_SUNEDU', limit: 200 }),
          fetchRegistros({ estado: 'ERROR_MINEDU', limit: 200 }),
        ])
        records = [...se, ...me]
      } else {
        const filter = TAB_FILTERS[tab] || {}
        records = await fetchRegistros({ ...filter, limit: 200 })
      }
      dispatch({ type: 'SET_RECORDS', payload: records })
    } catch { /* ignore */ }
  }, [dispatch])

  usePolling(poll, 2000)

  return (
    <div className="flex w-full h-screen bg-gray-50">
      <Sidebar />

      <main className="flex-1 flex flex-col relative overflow-hidden">
        <div className="p-6 md:p-8 flex flex-col h-full z-10 gap-5 overflow-y-auto">
          <MetricsGrid />
          <Pipeline />

          <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-5">
            <Terminal />
            <DataTable />
          </div>
        </div>
      </main>

      <ToastContainer />
    </div>
  )
}

export default function App() {
  return (
    <DashboardProvider>
      <DashboardContent />
    </DashboardProvider>
  )
}

import React, { memo, useCallback } from 'react'
import { useDashboard } from '../../context/DashboardContext'
import * as api from '../../api/client'

function Controls() {
  const { state, dispatch, addLog, showToast } = useDashboard()
  const { retry } = state

  const handleStart = useCallback(async () => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true })

      // Upload file if selected
      if (state.selectedFile) {
        addLog(`Uploading ${state.selectedFile.name}...`, 'text-neon-blue')
        const uploadRes = await api.uploadFile(state.selectedFile)
        addLog(`Loaded ${uploadRes.total_dnis} DNIs`, 'text-neon-green')
        showToast(`${uploadRes.total_dnis} DNIs loaded`, 'success')
        dispatch({ type: 'SET_FILE', payload: null })
      }

      addLog('Starting workers...', 'text-neon-blue')
      await api.startWorkers()
      addLog('Pipeline started!', 'text-neon-green')
      showToast('Pipeline started', 'success')
    } catch (e) {
      addLog(`Error: ${e.message}`, 'text-neon-red')
      showToast(e.message, 'error')
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false })
    }
  }, [state.selectedFile, dispatch, addLog, showToast])

  const handleStop = useCallback(async () => {
    try {
      await api.stopWorkers()
      addLog('Workers stopped', 'text-yellow-500')
      showToast('Pipeline stopped', 'warn')
    } catch (e) {
      addLog(`Error: ${e.message}`, 'text-neon-red')
      showToast(e.message, 'error')
    }
  }, [addLog, showToast])

  const handleClear = useCallback(async () => {
    try {
      await api.clearAll()
      dispatch({ type: 'CLEAR_LOGS' })
      dispatch({ type: 'SET_RECORDS', payload: [] })
      addLog('All data cleared', 'text-slate-400')
      showToast('Data cleared', 'success')
    } catch (e) {
      addLog(`Error: ${e.message}`, 'text-neon-red')
      showToast(e.message, 'error')
    }
  }, [dispatch, addLog, showToast])

  const handleRetry = useCallback(async () => {
    try {
      addLog('[RETRY] Re-encolando NOT_FOUND para nueva búsqueda...', 'text-yellow-500')
      const res = await api.retryNotFound()
      addLog(`[RETRY] ${res.reencolados} registros re-encolados`, 'text-neon-green')
      showToast(`${res.reencolados} DNIs re-encolados para reintento`, 'success')
    } catch (e) {
      addLog(`[RETRY] Error: ${e.message}`, 'text-neon-red')
      showToast(e.message, 'error')
    }
  }, [addLog, showToast])

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={handleStart}
          disabled={state.loading}
          className="col-span-2 py-3 px-4 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white rounded-lg font-bold flex items-center justify-center gap-2 shadow-neon-primary transition-all active:scale-95 group"
        >
          <span className="material-icons-round group-hover:animate-spin">play_circle</span>
          {state.loading ? 'STARTING...' : 'START PIPELINE'}
        </button>

        <button
          onClick={handleStop}
          className="py-2 px-3 border border-slate-600 hover:border-neon-red hover:text-neon-red hover:bg-neon-red/10 text-slate-300 rounded-lg font-medium flex items-center justify-center gap-2 transition-all active:scale-95"
        >
          <span className="material-icons-round text-sm">stop_circle</span>
          STOP
        </button>

        <button
          onClick={handleClear}
          className="py-2 px-3 border border-slate-600 hover:border-slate-400 text-slate-300 rounded-lg font-medium flex items-center justify-center gap-2 transition-all active:scale-95"
        >
          <span className="material-icons-round text-sm">cleaning_services</span>
          CLEAR
        </button>
      </div>

      {/* Retry Button — shown when pipeline is idle and there are retryable records */}
      {retry.can_retry && (
        <button
          onClick={handleRetry}
          className="w-full py-2.5 px-4 border border-yellow-500/40 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 hover:text-yellow-300 rounded-lg font-bold flex items-center justify-center gap-2 transition-all active:scale-95"
        >
          <span className="material-icons-round text-sm">replay</span>
          RETRY {retry.retryables} NOT FOUND
        </button>
      )}
    </div>
  )
}

export default memo(Controls)

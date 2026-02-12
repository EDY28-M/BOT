import React, { memo, useCallback, useState } from 'react'
import { useDashboard } from '../../context/DashboardContext'
import * as api from '../../api/client'

function Controls() {
  const { state, dispatch, addLog, showToast } = useDashboard()
  const { retry } = state
  const [showInvalid, setShowInvalid] = useState(false)

  const handleStart = useCallback(async () => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true })

      if (state.selectedFile) {
        addLog(`Subiendo ${state.selectedFile.name}...`, 'text-blue-600')
        const uploadRes = await api.uploadFile(state.selectedFile)

        if (uploadRes.total_dnis > 0) {
          addLog(`✓ ${uploadRes.total_dnis} DNIs válidos cargados`, 'text-green-600')
        }

        if (uploadRes.invalid_dnis && uploadRes.invalid_dnis.length > 0) {
          dispatch({ type: 'SET_INVALID_DNIS', payload: uploadRes.invalid_dnis })
          addLog(`⚠ ${uploadRes.total_invalid} DNIs inválidos (no tienen 8 dígitos)`, 'text-amber-600')
          for (const d of uploadRes.invalid_dnis) {
            addLog(`  ✗ "${d}" — formato incorrecto`, 'text-amber-500')
          }
        } else {
          dispatch({ type: 'SET_INVALID_DNIS', payload: [] })
        }

        if (uploadRes.total_dnis > 0) {
          showToast(`${uploadRes.total_dnis} DNIs cargados${uploadRes.total_invalid > 0 ? ` (${uploadRes.total_invalid} rechazados)` : ''}`, 'success')
        } else {
          showToast(`No hay DNIs válidos. ${uploadRes.total_invalid} rechazados.`, 'error')
        }

        dispatch({ type: 'SET_FILE', payload: null })
      }

      addLog('Iniciando workers...', 'text-blue-600')
      const startRes = await api.startWorkers()

      if (startRes.recovered > 0) {
        addLog(`🔄 ${startRes.recovered} DNIs atascados recuperados automáticamente`, 'text-amber-600')
        showToast(`${startRes.recovered} DNIs recuperados`, 'warn')
      }

      addLog('¡Pipeline iniciado!', 'text-green-600')
      showToast('Pipeline iniciado', 'success')
    } catch (e) {
      addLog(`Error: ${e.message}`, 'text-red-500')
      showToast(e.message, 'error')
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false })
    }
  }, [state.selectedFile, dispatch, addLog, showToast])

  const handleStop = useCallback(async () => {
    try {
      await api.stopWorkers()
      addLog('Workers detenidos', 'text-amber-600')
      showToast('Pipeline detenido', 'warn')
    } catch (e) {
      addLog(`Error: ${e.message}`, 'text-red-500')
      showToast(e.message, 'error')
    }
  }, [addLog, showToast])

  const handleClear = useCallback(async () => {
    try {
      await api.clearAll()
      dispatch({ type: 'CLEAR_LOGS' })
      dispatch({ type: 'SET_RECORDS', payload: [] })
      dispatch({ type: 'SET_INVALID_DNIS', payload: [] })
      addLog('Datos limpiados', 'text-gray-500')
      showToast('Datos limpiados', 'success')
    } catch (e) {
      addLog(`Error: ${e.message}`, 'text-red-500')
      showToast(e.message, 'error')
    }
  }, [dispatch, addLog, showToast])

  const handleRetry = useCallback(async () => {
    try {
      addLog('[REINTENTO] Re-encolando NO ENCONTRADOS...', 'text-amber-600')
      const res = await api.retryNotFound()
      addLog(`[REINTENTO] ${res.reencolados} registros re-encolados`, 'text-green-600')
      showToast(`${res.reencolados} DNIs re-encolados`, 'success')
    } catch (e) {
      addLog(`[REINTENTO] Error: ${e.message}`, 'text-red-500')
      showToast(e.message, 'error')
    }
  }, [addLog, showToast])

  const handleRecover = useCallback(async () => {
    try {
      addLog('[RECUPERAR] Recuperando DNIs atascados...', 'text-amber-600')
      const res = await api.recoverStuck()
      addLog(`[RECUPERAR] ${res.message}`, 'text-green-600')
      showToast(res.message, 'success')
    } catch (e) {
      addLog(`[RECUPERAR] Error: ${e.message}`, 'text-red-500')
      showToast(e.message, 'error')
    }
  }, [addLog, showToast])

  const stuckCount = (state.conteos?.PROCESANDO_SUNEDU || 0) + (state.conteos?.PROCESANDO_MINEDU || 0)

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={handleStart}
          disabled={state.loading}
          className="col-span-2 py-3 px-4 bg-primary hover:bg-primary-dark disabled:opacity-50 text-white rounded-lg font-bold flex items-center justify-center gap-2 shadow-btn transition-all active:scale-[0.98]"
        >
          <span className="material-icons-round">play_circle</span>
          {state.loading ? 'INICIANDO...' : 'INICIAR CONSULTA'}
        </button>

        <button
          onClick={handleStop}
          className="py-2 px-3 border border-gray-300 hover:border-red-400 hover:text-red-600 hover:bg-red-50 text-gray-600 rounded-lg font-medium flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
        >
          <span className="material-icons-round text-sm">stop_circle</span>
          DETENER
        </button>

        <button
          onClick={handleClear}
          className="py-2 px-3 border border-gray-300 hover:border-gray-400 text-gray-600 rounded-lg font-medium flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
        >
          <span className="material-icons-round text-sm">cleaning_services</span>
          LIMPIAR
        </button>
      </div>

      {retry.can_retry && (
        <button
          onClick={handleRetry}
          className="w-full py-2.5 px-4 border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-700 rounded-lg font-bold flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
        >
          <span className="material-icons-round text-sm">replay</span>
          REINTENTAR {retry.retryables} NO ENCONTRADOS
        </button>
      )}

      {stuckCount > 0 && !state.workers?.sunedu?.running && (
        <button
          onClick={handleRecover}
          className="w-full py-2 px-4 border border-orange-300 bg-orange-50 hover:bg-orange-100 text-orange-700 rounded-lg font-bold flex items-center justify-center gap-2 transition-all active:scale-[0.98] text-sm"
        >
          <span className="material-icons-round text-sm">refresh</span>
          RECUPERAR {stuckCount} ATASCADOS
        </button>
      )}

      {state.invalidDnis.length > 0 && (
        <div className="border border-amber-200 bg-amber-50 rounded-lg overflow-hidden">
          <button
            onClick={() => setShowInvalid(!showInvalid)}
            className="w-full px-3 py-2 flex items-center justify-between text-amber-700 hover:bg-amber-100 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="material-icons-round text-sm">warning</span>
              <span className="text-xs font-bold">{state.invalidDnis.length} DNIs INVÁLIDOS</span>
            </div>
            <span className="material-icons-round text-sm transition-transform" style={{ transform: showInvalid ? 'rotate(180deg)' : '' }}>
              expand_more
            </span>
          </button>
          {showInvalid && (
            <div className="px-3 pb-2 max-h-32 overflow-y-auto">
              <p className="text-[10px] text-amber-600 mb-1">No se procesaron (deben tener 8 dígitos):</p>
              <div className="flex flex-wrap gap-1">
                {state.invalidDnis.map((d, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 text-xs font-mono bg-amber-100 text-amber-700 rounded border border-amber-200"
                  >
                    {d}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default memo(Controls)

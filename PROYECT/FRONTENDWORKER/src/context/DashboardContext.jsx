import React, { createContext, useContext, useReducer, useCallback, useRef } from 'react'
import { ts } from '../utils/formatters'

const MAX_LOGS = 40

const initialState = {
  // Status
  total: 0,
  terminados: 0,
  en_proceso: 0,
  progreso_pct: 0,
  conteos: {},
  pipeline: { sunedu: {}, minedu: {} },
  // Retry
  retry: { retryables: 0, pipeline_idle: false, can_retry: false },
  // Workers
  workers: { sunedu: { running: false }, minedu: { running: false } },
  // Records
  records: [],
  // Terminal
  logs: [{ time: ts(), msg: 'Initializing dashboard...', color: 'text-slate-500' }],
  // UI
  currentTab: 'all',
  selectedFile: null,
  loading: false,
  // Toasts
  toasts: [],
}

function reducer(state, action) {
  switch (action.type) {
    case 'SET_STATUS':
      return { ...state, ...action.payload }
    case 'SET_WORKERS':
      return { ...state, workers: action.payload }
    case 'SET_RECORDS':
      return { ...state, records: action.payload }
    case 'SET_TAB':
      return { ...state, currentTab: action.payload }
    case 'SET_FILE':
      return { ...state, selectedFile: action.payload }
    case 'SET_LOADING':
      return { ...state, loading: action.payload }
    case 'ADD_LOG': {
      const logs = [...state.logs, action.payload]
      return { ...state, logs: logs.length > MAX_LOGS ? logs.slice(-MAX_LOGS) : logs }
    }
    case 'CLEAR_LOGS':
      return { ...state, logs: [] }
    case 'ADD_TOAST': {
      return { ...state, toasts: [...state.toasts, action.payload] }
    }
    case 'REMOVE_TOAST':
      return { ...state, toasts: state.toasts.filter(t => t.id !== action.payload) }
    default:
      return state
  }
}

const DashboardContext = createContext(null)

export function DashboardProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState)
  const toastId = useRef(0)

  const addLog = useCallback((msg, color = 'text-slate-400') => {
    dispatch({ type: 'ADD_LOG', payload: { time: ts(), msg, color } })
  }, [])

  const showToast = useCallback((msg, type = 'success') => {
    const id = ++toastId.current
    dispatch({ type: 'ADD_TOAST', payload: { id, msg, type } })
    setTimeout(() => dispatch({ type: 'REMOVE_TOAST', payload: id }), 3500)
  }, [])

  return (
    <DashboardContext.Provider value={{ state, dispatch, addLog, showToast }}>
      {children}
    </DashboardContext.Provider>
  )
}

export function useDashboard() {
  const ctx = useContext(DashboardContext)
  if (!ctx) throw new Error('useDashboard must be inside DashboardProvider')
  return ctx
}

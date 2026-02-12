import React, { memo, useMemo, useCallback } from 'react'
import { useDashboard } from '../../context/DashboardContext'
import { SourceBadge, StatusIcon } from '../../utils/badges'
import TabBar from './TabBar'
import { downloadResultados } from '../../api/client'

const COLUMNS = {
  all: ['ID', 'DNI', 'Nombre Completo', 'Institución', 'Fuente', 'Estado'],
  sunedu: ['ID', 'DNI', 'Nombre Completo', 'Grado', 'Institución', 'Fecha Diploma'],
  minedu: ['ID', 'DNI', 'Nombre Completo', 'Título', 'Institución', 'Fecha'],
  notfound: ['ID', 'DNI', 'Motivo', 'Reintentos', 'Actualizado'],
  errors: ['ID', 'DNI', 'Worker', 'Detalle Error', 'Hora'],
}

function RowAll({ r }) {
  const name = r.sunedu_nombres || r.minedu_nombres || '—'
  const inst = r.sunedu_institucion || r.minedu_institucion || '—'
  return (
    <tr className="hover:bg-blue-50/50 transition-colors">
      <td className="px-4 py-3 font-mono text-xs text-gray-400">#{String(r.id).padStart(5, '0')}</td>
      <td className="px-4 py-3 text-gray-700 font-medium">{r.dni}</td>
      <td className="px-4 py-3 text-gray-900 font-medium">{name}</td>
      <td className="px-4 py-3 text-gray-500">{inst}</td>
      <td className="px-4 py-3"><SourceBadge estado={r.estado} /></td>
      <td className="px-4 py-3"><StatusIcon estado={r.estado} /></td>
    </tr>
  )
}

function RowSunedu({ r }) {
  return (
    <tr className="hover:bg-blue-50/50 transition-colors">
      <td className="px-4 py-3 font-mono text-xs text-gray-400">#{String(r.id).padStart(5, '0')}</td>
      <td className="px-4 py-3 text-gray-700 font-medium">{r.dni}</td>
      <td className="px-4 py-3 text-gray-900 font-medium">{r.sunedu_nombres || '—'}</td>
      <td className="px-4 py-3 text-gray-500">{r.sunedu_grado || '—'}</td>
      <td className="px-4 py-3 text-gray-500">{r.sunedu_institucion || '—'}</td>
      <td className="px-4 py-3 text-gray-500 font-mono text-xs">{r.sunedu_fecha_diploma || '—'}</td>
    </tr>
  )
}

function RowMinedu({ r }) {
  return (
    <tr className="hover:bg-blue-50/50 transition-colors">
      <td className="px-4 py-3 font-mono text-xs text-gray-400">#{String(r.id).padStart(5, '0')}</td>
      <td className="px-4 py-3 text-gray-700 font-medium">{r.dni}</td>
      <td className="px-4 py-3 text-gray-900 font-medium">{r.minedu_nombres || '—'}</td>
      <td className="px-4 py-3 text-gray-500">{r.minedu_titulo || '—'}</td>
      <td className="px-4 py-3 text-gray-500">{r.minedu_institucion || '—'}</td>
      <td className="px-4 py-3 text-gray-500 font-mono text-xs">{r.minedu_fecha || '—'}</td>
    </tr>
  )
}

function RowNotFound({ r }) {
  return (
    <tr className="hover:bg-blue-50/50 transition-colors">
      <td className="px-4 py-3 font-mono text-xs text-gray-400">#{String(r.id).padStart(5, '0')}</td>
      <td className="px-4 py-3 text-gray-700 font-medium">{r.dni}</td>
      <td className="px-4 py-3 text-red-500">{r.error_msg || 'Sin registros en ambas bases de datos'}</td>
      <td className="px-4 py-3 text-center">
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700">
          {r.retry_count || 0}
        </span>
      </td>
      <td className="px-4 py-3 text-gray-400 font-mono text-xs">{r.updated_at?.slice(11, 19) || '—'}</td>
    </tr>
  )
}

function RowError({ r }) {
  return (
    <tr className="hover:bg-blue-50/50 transition-colors">
      <td className="px-4 py-3 font-mono text-xs text-gray-400">#{String(r.id).padStart(5, '0')}</td>
      <td className="px-4 py-3 text-gray-700 font-medium">{r.dni}</td>
      <td className="px-4 py-3"><SourceBadge estado={r.estado} /></td>
      <td className="px-4 py-3 text-red-500 text-xs">{r.error_msg || '—'}</td>
      <td className="px-4 py-3 text-gray-400 font-mono text-xs">{r.updated_at?.slice(11, 19) || '—'}</td>
    </tr>
  )
}

const ROW_MAP = {
  all: RowAll,
  sunedu: RowSunedu,
  minedu: RowMinedu,
  notfound: RowNotFound,
  errors: RowError,
}

function DataTable() {
  const { state, showToast } = useDashboard()
  const { records, currentTab, total } = state
  const cols = COLUMNS[currentTab]
  const RowComponent = ROW_MAP[currentTab]

  const handleDownload = useCallback(async () => {
    try {
      await downloadResultados()
      showToast('Descarga iniciada', 'success')
    } catch (e) {
      showToast(e.message, 'error')
    }
  }, [showToast])

  return (
    <div className="lg:w-2/3 card-panel rounded-xl flex flex-col overflow-hidden">
      <TabBar />

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-gray-50 text-gray-500 font-medium sticky top-0 z-10 border-b border-gray-200">
            <tr>
              {cols.map(h => (
                <th key={h} className={`px-4 py-3 ${h === 'ID' ? 'font-mono text-xs' : ''}`}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {records.length === 0 ? (
              <tr>
                <td colSpan={cols.length} className="px-4 py-16 text-center">
                  <span className="material-icons-round text-5xl text-gray-200 block mb-3">inbox</span>
                  <p className="text-gray-400 text-sm">Sin registros. Sube un archivo e inicia la consulta.</p>
                </td>
              </tr>
            ) : (
              records.map(r => <RowComponent key={r.id} r={r} />)
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-gray-200 bg-gray-50 flex justify-between items-center text-xs text-gray-500 shrink-0">
        <span>Mostrando {records.length} de {total} registros</span>
        <button
          onClick={handleDownload}
          className="flex items-center gap-1 text-primary hover:text-primary-dark font-medium transition-colors"
        >
          <span className="material-icons-round text-sm">download</span>
          Exportar XLSX
        </button>
      </div>
    </div>
  )
}

export default memo(DataTable)

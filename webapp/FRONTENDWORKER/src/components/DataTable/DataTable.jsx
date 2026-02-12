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

function MobileCard({ r, cols, RowComp }) {
  // Extract data using the same logic as Rows (or simplify)
  // For simplicity, we'll map columns to values if possible, or just render a generic cart
  // But Row components are specialized. Let's use a generic approach for the card
  // or specific cards. 
  // Better approach: Render the Row cells as a list.

  return (
    <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 flex flex-col gap-3 relative overflow-hidden">
      <div className="flex justify-between items-start">
        <span className="font-mono text-xs text-gray-400">#{String(r.id).padStart(5, '0')}</span>
        <div className="flex gap-2">
          <SourceBadge estado={r.estado} />
          <StatusIcon estado={r.estado} />
        </div>
      </div>

      <div>
        <div className="font-bold text-gray-900 text-base">{r.dni}</div>
        <div className="text-sm text-gray-800 font-medium">
          {r.sunedu_nombres || r.minedu_nombres || '—'}
        </div>
      </div>

      <div className="space-y-1 text-xs text-gray-600 bg-gray-50 p-2 rounded border border-gray-100">
        {(r.sunedu_grado || r.minedu_titulo) && (
          <div className="flex flex-col">
            <span className="text-[10px] text-gray-400 uppercase tracking-wider font-bold">Grado/Título</span>
            <span className="font-medium text-gray-800">{r.sunedu_grado || r.minedu_titulo}</span>
          </div>
        )}

        {(r.sunedu_institucion || r.minedu_institucion) && (
          <div className="flex flex-col mt-1">
            <span className="text-[10px] text-gray-400 uppercase tracking-wider font-bold">Institución</span>
            <span>{r.sunedu_institucion || r.minedu_institucion}</span>
          </div>
        )}

        {(r.sunedu_fecha_diploma || r.minedu_fecha) && (
          <div className="flex flex-col mt-1">
            <span className="text-[10px] text-gray-400 uppercase tracking-wider font-bold">Fecha</span>
            <span className="font-mono">{r.sunedu_fecha_diploma || r.minedu_fecha}</span>
          </div>
        )}
      </div>

      {r.error_msg && (
        <div className="text-xs text-red-500 bg-red-50 p-2 rounded border border-red-100">
          {r.error_msg}
        </div>
      )}

      {r.updated_at && (
        <div className="text-[10px] text-gray-300 text-right mt-1">
          Act: {r.updated_at.slice(11, 19)}
        </div>
      )}
    </div>
  )
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
      <div className="flex-1 overflow-auto overflow-x-auto">
        {/* Mobile Cards (Visible below md) */}
        <div className="md:hidden space-y-3 p-4 bg-gray-50">
          {records.map(r => (
            <MobileCard key={r.id} r={r} />
          ))}
          {records.length === 0 && (
            <div className="text-center py-10 text-gray-400 text-sm">
              Sin registros
            </div>
          )}
        </div>

        {/* Desktop Table (Visible md+) */}
        <table className="w-full text-left text-sm whitespace-nowrap hidden md:table">
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

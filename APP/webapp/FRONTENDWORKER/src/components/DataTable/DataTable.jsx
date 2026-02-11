import React, { memo, useMemo, useCallback } from 'react'
import { useDashboard } from '../../context/DashboardContext'
import { SourceBadge, StatusIcon } from '../../utils/badges'
import TabBar from './TabBar'
import { downloadResultados } from '../../api/client'

const COLUMNS = {
  all: ['ID', 'DNI', 'Full Name', 'Institution', 'Source', 'Status'],
  sunedu: ['ID', 'DNI', 'Full Name', 'Degree', 'Institution', 'Diploma Date'],
  minedu: ['ID', 'DNI', 'Full Name', 'Title', 'Institution', 'Date'],
  notfound: ['ID', 'DNI', 'Reason', 'Retries', 'Updated'],
  errors: ['ID', 'DNI', 'Worker', 'Error Detail', 'When'],
}

function RowAll({ r }) {
  const name = r.sunedu_nombres || r.minedu_nombres || '—'
  const inst = r.sunedu_institucion || r.minedu_institucion || '—'
  return (
    <tr className="hover:bg-primary/5 transition-colors">
      <td className="px-4 py-3 font-mono text-xs text-slate-500">#{String(r.id).padStart(5, '0')}</td>
      <td className="px-4 py-3 text-slate-300">{r.dni}</td>
      <td className="px-4 py-3 text-white font-medium">{name}</td>
      <td className="px-4 py-3 text-slate-400">{inst}</td>
      <td className="px-4 py-3"><SourceBadge estado={r.estado} /></td>
      <td className="px-4 py-3"><StatusIcon estado={r.estado} /></td>
    </tr>
  )
}

function RowSunedu({ r }) {
  return (
    <tr className="hover:bg-primary/5 transition-colors">
      <td className="px-4 py-3 font-mono text-xs text-slate-500">#{String(r.id).padStart(5, '0')}</td>
      <td className="px-4 py-3 text-slate-300">{r.dni}</td>
      <td className="px-4 py-3 text-white font-medium">{r.sunedu_nombres || '—'}</td>
      <td className="px-4 py-3 text-slate-400">{r.sunedu_grado || '—'}</td>
      <td className="px-4 py-3 text-slate-400">{r.sunedu_institucion || '—'}</td>
      <td className="px-4 py-3 text-slate-400 font-mono text-xs">{r.sunedu_fecha_diploma || '—'}</td>
    </tr>
  )
}

function RowMinedu({ r }) {
  return (
    <tr className="hover:bg-primary/5 transition-colors">
      <td className="px-4 py-3 font-mono text-xs text-slate-500">#{String(r.id).padStart(5, '0')}</td>
      <td className="px-4 py-3 text-slate-300">{r.dni}</td>
      <td className="px-4 py-3 text-white font-medium">{r.minedu_nombres || '—'}</td>
      <td className="px-4 py-3 text-slate-400">{r.minedu_titulo || '—'}</td>
      <td className="px-4 py-3 text-slate-400">{r.minedu_institucion || '—'}</td>
      <td className="px-4 py-3 text-slate-400 font-mono text-xs">{r.minedu_fecha || '—'}</td>
    </tr>
  )
}

function RowNotFound({ r }) {
  return (
    <tr className="hover:bg-primary/5 transition-colors">
      <td className="px-4 py-3 font-mono text-xs text-slate-500">#{String(r.id).padStart(5, '0')}</td>
      <td className="px-4 py-3 text-slate-300">{r.dni}</td>
      <td className="px-4 py-3 text-neon-red">{r.error_msg || 'No records in both databases'}</td>
      <td className="px-4 py-3 text-center">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-yellow-500/10 text-yellow-500 border border-yellow-500/20">
          {r.retry_count || 0}
        </span>
      </td>
      <td className="px-4 py-3 text-slate-500 font-mono text-xs">{r.updated_at?.slice(11, 19) || '—'}</td>
    </tr>
  )
}

function RowError({ r }) {
  const worker = r.estado?.includes('SUNEDU') ? 'SUNEDU' : 'MINEDU'
  return (
    <tr className="hover:bg-primary/5 transition-colors">
      <td className="px-4 py-3 font-mono text-xs text-slate-500">#{String(r.id).padStart(5, '0')}</td>
      <td className="px-4 py-3 text-slate-300">{r.dni}</td>
      <td className="px-4 py-3"><SourceBadge estado={r.estado} /></td>
      <td className="px-4 py-3 text-neon-red text-xs">{r.error_msg || '—'}</td>
      <td className="px-4 py-3 text-slate-500 font-mono text-xs">{r.updated_at?.slice(11, 19) || '—'}</td>
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
      showToast('Download started', 'success')
    } catch (e) {
      showToast(e.message, 'error')
    }
  }, [showToast])

  return (
    <div className="lg:w-2/3 glass-panel rounded-xl border border-primary/20 flex flex-col overflow-hidden">
      <TabBar />

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-primary/10 text-slate-300 font-medium sticky top-0 backdrop-blur-md z-10">
            <tr>
              {cols.map(h => (
                <th key={h} className={`px-4 py-3 ${h === 'ID' ? 'font-mono text-xs' : ''}`}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {records.length === 0 ? (
              <tr>
                <td colSpan={cols.length} className="px-4 py-16 text-center">
                  <span className="material-icons-round text-5xl text-slate-700 block mb-3">inbox</span>
                  <p className="text-slate-500 text-sm">No records yet. Upload a file and start the pipeline.</p>
                </td>
              </tr>
            ) : (
              records.map(r => <RowComponent key={r.id} r={r} />)
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-slate-800 bg-primary/5 flex justify-between items-center text-xs text-slate-400 shrink-0">
        <span>Showing {records.length} of {total} records</span>
        <button
          onClick={handleDownload}
          className="flex items-center gap-1 text-primary hover:text-white transition-colors"
        >
          <span className="material-icons-round text-sm">download</span>
          Export XLSX
        </button>
      </div>
    </div>
  )
}

export default memo(DataTable)

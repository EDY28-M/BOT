import React, { memo } from 'react'
import { useDashboard } from '../../context/DashboardContext'
import WorkerCard from './WorkerCard'
import FileUpload from './FileUpload'
import Controls from './Controls'
import logoImg from '../../public/TITULA.jpg'

function Sidebar({ isOpen, onClose }) {
  const { state } = useDashboard()
  const { workers } = state

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 md:hidden"
          onClick={onClose}
        />
      )}

      <aside className={`
        fixed md:static inset-y-0 left-0 z-30
        w-80 bg-white border-r border-gray-200 flex flex-col justify-between shrink-0 shadow-sm
        transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        <div className="p-6">
          {/* Branding */}
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <img src={logoImg} alt="SICGT" className="h-11 w-auto object-contain" />
              <div>
                <h1 className="font-bold text-lg leading-tight tracking-wide text-gray-900">
                  SICGT
                </h1>
                <p className="text-[10px] text-gray-400 font-medium tracking-wide">
                  Sistema de Consulta de Grados y Títulos
                </p>
              </div>
            </div>

            {/* Mobile Close Button */}
            <button
              onClick={onClose}
              className="md:hidden p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
            >
              <span className="material-icons-round">close</span>
            </button>
          </div>

          {/* Worker Status */}
          <div className="space-y-3 mb-8">
            <h3 className="text-xs uppercase tracking-widest text-gray-400 font-bold mb-2">Estado del Sistema</h3>
            <WorkerCard name="sunedu" running={workers.sunedu?.running} />
            <WorkerCard name="minedu" running={workers.minedu?.running} />
          </div>

          {/* File Upload */}
          <FileUpload />

          {/* Controls */}
          <Controls />
        </div>

        <div className="p-4 border-t border-gray-100 text-center">
          <p className="text-[10px] text-gray-400 font-medium">SICGT v3.0 — Conexión Segura</p>
        </div>
      </aside>
    </>
  )
}

export default memo(Sidebar)

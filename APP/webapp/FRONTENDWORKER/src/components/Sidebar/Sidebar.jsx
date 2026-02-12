import React, { memo } from 'react'
import { useDashboard } from '../../context/DashboardContext'
import WorkerCard from './WorkerCard'
import FileUpload from './FileUpload'
import Controls from './Controls'
import logoImg from '../../public/TITULA.jpg'

function Sidebar() {
  const { state } = useDashboard()
  const { workers } = state

  return (
    <aside className="w-80 bg-white border-r border-gray-200 flex flex-col justify-between shrink-0 z-20 shadow-sm">
      <div className="p-6">
        {/* Branding */}
        <div className="flex items-center gap-3 mb-8">
          <img src={logoImg} alt="SICGTD" className="h-11 w-auto object-contain" />
          <div>
            <h1 className="font-bold text-lg leading-tight tracking-wide text-gray-900">
              SICGTD
            </h1>
            <p className="text-[10px] text-gray-400 font-medium tracking-wide">
              Sistema de Consulta de Grados y Títulos
            </p>
          </div>
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
        <p className="text-[10px] text-gray-400 font-medium">SICGTD v3.0 — Conexión Segura</p>
      </div>
    </aside>
  )
}

export default memo(Sidebar)

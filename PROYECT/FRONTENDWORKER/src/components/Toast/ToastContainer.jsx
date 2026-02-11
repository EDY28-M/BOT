import React, { memo } from 'react'
import { useDashboard } from '../../context/DashboardContext'

const TYPE_STYLES = {
  success: 'bg-neon-green/15 border-neon-green/30 text-neon-green',
  error: 'bg-neon-red/15 border-neon-red/30 text-neon-red',
  warn: 'bg-yellow-500/15 border-yellow-500/30 text-yellow-500',
}

function ToastContainer() {
  const { state } = useDashboard()

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 pointer-events-none">
      {state.toasts.map(toast => (
        <div
          key={toast.id}
          className={`px-4 py-3 rounded-lg border text-sm font-semibold font-display
            transition-all duration-300 transform pointer-events-auto
            ${TYPE_STYLES[toast.type] || TYPE_STYLES.success}
            animate-[slideIn_0.3s_ease-out]`}
          style={{ maxWidth: 360 }}
        >
          {toast.msg}
        </div>
      ))}
    </div>
  )
}

export default memo(ToastContainer)

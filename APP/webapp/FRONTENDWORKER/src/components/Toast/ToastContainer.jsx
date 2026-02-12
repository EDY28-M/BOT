import React, { memo } from 'react'
import { useDashboard } from '../../context/DashboardContext'

const TYPE_STYLES = {
  success: 'bg-green-50 border-green-200 text-green-700',
  error: 'bg-red-50 border-red-200 text-red-700',
  warn: 'bg-amber-50 border-amber-200 text-amber-700',
}

function ToastContainer() {
  const { state } = useDashboard()

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 pointer-events-none">
      {state.toasts.map(toast => (
        <div
          key={toast.id}
          className={`px-4 py-3 rounded-lg border text-sm font-semibold font-display shadow-card
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

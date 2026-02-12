import React, { useRef, useCallback, memo } from 'react'
import { useDashboard } from '../../context/DashboardContext'

function FileUpload() {
  const { state, dispatch, addLog } = useDashboard()
  const inputRef = useRef(null)
  const dropRef = useRef(null)

  const selectFile = useCallback((file) => {
    dispatch({ type: 'SET_FILE', payload: file })
    addLog(`Archivo seleccionado: ${file.name}`, 'text-gray-500')
  }, [dispatch, addLog])

  const clearFile = useCallback(() => {
    dispatch({ type: 'SET_FILE', payload: null })
    if (inputRef.current) inputRef.current.value = ''
  }, [dispatch])

  const onDragOver = (e) => {
    e.preventDefault()
    dropRef.current?.classList.add('drop-active')
  }
  const onDragLeave = () => dropRef.current?.classList.remove('drop-active')
  const onDrop = (e) => {
    e.preventDefault()
    dropRef.current?.classList.remove('drop-active')
    if (e.dataTransfer.files.length) selectFile(e.dataTransfer.files[0])
  }
  const onChange = (e) => {
    if (e.target.files.length) selectFile(e.target.files[0])
  }

  return (
    <div className="mb-6">
      <h3 className="text-xs uppercase tracking-widest text-gray-400 font-bold mb-2">Archivo de Entrada</h3>

      <div
        ref={dropRef}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className="border-2 border-dashed border-gray-300 hover:border-primary hover:bg-blue-50 transition-all rounded-xl p-6 text-center cursor-pointer group relative overflow-hidden"
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={onChange}
          className="hidden"
        />
        <span className="material-icons-round text-4xl text-gray-300 group-hover:text-primary transition-colors mb-2 block">
          cloud_upload
        </span>
        <p className="text-sm text-gray-500 font-medium group-hover:text-gray-700">
          {state.selectedFile ? 'Archivo seleccionado' : 'Arrastra CSV/XLSX aquí'}
        </p>
        <p className="text-xs text-gray-400 mt-1">Máx 50MB</p>
      </div>

      {state.selectedFile && (
        <div className="mt-3 p-3 rounded-lg bg-blue-50 border border-blue-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              <span className="material-icons-round text-primary text-sm">description</span>
              <span className="text-sm text-gray-700 truncate font-medium">{state.selectedFile.name}</span>
            </div>
            <button onClick={clearFile} className="text-gray-400 hover:text-red-500 transition-colors ml-2 shrink-0">
              <span className="material-icons-round text-sm">close</span>
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-1 font-mono">
            {(state.selectedFile.size / 1024).toFixed(1)} KB
          </p>
        </div>
      )}
    </div>
  )
}

export default memo(FileUpload)

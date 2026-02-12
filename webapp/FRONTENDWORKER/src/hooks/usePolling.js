import { useEffect, useRef, useCallback } from 'react'

/**
 * Custom hook for polling at a fixed interval.
 * Calls `callback` immediately, then every `delay` ms.
 * Pauses when the tab is hidden.
 */
export default function usePolling(callback, delay = 2000) {
  const savedCb = useRef(callback)
  const timerRef = useRef(null)

  useEffect(() => {
    savedCb.current = callback
  }, [callback])

  const tick = useCallback(async () => {
    try { await savedCb.current() } catch { /* swallow */ }
  }, [])

  useEffect(() => {
    tick() // immediate first call
    timerRef.current = setInterval(tick, delay)

    const onVisibility = () => {
      if (document.hidden) {
        clearInterval(timerRef.current)
      } else {
        tick()
        timerRef.current = setInterval(tick, delay)
      }
    }
    document.addEventListener('visibilitychange', onVisibility)

    return () => {
      clearInterval(timerRef.current)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [delay, tick])
}

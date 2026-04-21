import React, { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'

export default function PortalModal({ children, open = false, onClose, overlayClassName, innerClassName, closeDuration = 220 }) {
  const [mounted, setMounted] = useState(open)
  const [closing, setClosing] = useState(false)

  useEffect(() => {
    if (open) {
      setMounted(true)
      setClosing(false)
    } else if (mounted) {
      setClosing(true)
      const t = setTimeout(() => {
        setMounted(false)
        setClosing(false)
      }, closeDuration)
      return () => clearTimeout(t)
    }
  }, [open, mounted, closeDuration])

  useEffect(() => {
    if (!mounted) return
    function handleKey(e) {
      if (e.key === 'Escape') onClose && onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [mounted, onClose])

  if (typeof document === 'undefined') return null
  if (!mounted) return null

  const overlayBase = overlayClassName || 'fixed inset-0 z-[70] flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm'
  const innerBase = innerClassName || ''

  const overlayStateClass = open && !closing ? 'modal-overlay-enter' : 'modal-overlay-exit'
  const innerStateClass = open && !closing ? 'modal-content-enter' : 'modal-content-exit'

  return createPortal(
    <div className={`${overlayBase} ${overlayStateClass}`} onClick={() => onClose && onClose()}>
      <div className={`${innerBase} ${innerStateClass}`} onClick={(e) => e.stopPropagation()}>
        {typeof children === 'function' ? children({ close: onClose }) : children}
      </div>
    </div>,
    document.body
  )
}

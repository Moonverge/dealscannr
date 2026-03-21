import { useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import { cn } from '@/lib/cn'

export function Modal({
  open,
  onClose,
  title,
  children,
  className,
  panelClassName,
}: {
  open: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  className?: string
  panelClassName?: string
}) {
  const titleId = useId()
  const panelRef = useRef<HTMLDivElement>(null)
  const prevFocus = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!open) return
    prevFocus.current = document.activeElement as HTMLElement | null
    const panel = panelRef.current
    const focusable = panel?.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    )
    focusable?.[0]?.focus()

    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }
      if (e.key !== 'Tab' || !panel) return
      const nodes = panel.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      )
      if (nodes.length === 0) return
      const first = nodes[0]
      const last = nodes[nodes.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      prevFocus.current?.focus?.()
    }
  }, [open, onClose])

  if (!open) return null

  return createPortal(
    <div className={cn('fixed inset-0 z-[100]', className)}>
      <button
        type="button"
        className="absolute inset-0 bg-[var(--overlay)] backdrop-blur-[4px]"
        aria-label="Close dialog"
        onClick={onClose}
      />
      <div className="pointer-events-none fixed inset-0 flex items-center justify-center p-4">
        <div
          ref={panelRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby={title ? titleId : undefined}
          className={cn(
            'ds-modal-panel pointer-events-auto relative max-h-[90vh] w-full max-w-md overflow-auto rounded-[var(--radius-xl)] border border-[var(--border)] bg-[var(--surface)] shadow-dsLg',
            panelClassName,
          )}
        >
          <button
            type="button"
            onClick={onClose}
            className="absolute right-3 top-3 z-10 rounded-[var(--radius-sm)] p-2 text-[var(--textMuted)] hover:bg-[var(--surface2)] hover:text-[var(--text)]"
            aria-label="Close"
          >
            <X className="h-5 w-5" strokeWidth={2} />
          </button>
          {title && (
            <h2
              id={titleId}
              className="border-b border-[var(--border)] px-5 py-4 pr-14 font-display text-lg font-semibold text-[var(--text)]"
            >
              {title}
            </h2>
          )}
          <div className={cn('p-5', !title && 'pt-14')}>{children}</div>
        </div>
      </div>
    </div>,
    document.body,
  )
}

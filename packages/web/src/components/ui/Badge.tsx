import { cn } from '@/lib/cn'
import { normalizeVerdict, verdictStyles } from '@/lib/verdict-styles'

type VSize = 'sm' | 'lg'

export function VerdictBadge({
  verdict,
  size = 'sm',
  className,
  pulse = false,
}: {
  verdict: string | null | undefined
  size?: VSize
  className?: string
  /** Brief scale animation on first paint */
  pulse?: boolean
}) {
  const key = normalizeVerdict(verdict)
  const s = verdictStyles(key)
  const label = verdict?.toUpperCase().trim() || '—'

  return (
    <span
      className={cn(
        'inline-flex items-center justify-center rounded-[var(--radius-sm)] border font-mono font-medium uppercase tracking-[0.05em]',
        pulse && 'ds-verdict-pop',
        size === 'sm' && 'px-2 py-0.5 text-[11px]',
        size === 'lg' && 'px-3 py-1.5 text-sm',
        className,
      )}
      style={{
        color: s.color,
        backgroundColor: s.bg,
        borderColor: s.border,
      }}
    >
      {label}
    </span>
  )
}

export function StatusDot({ status }: { status: string }) {
  const base = 'inline-block h-2.5 w-2.5 shrink-0 rounded-full'
  if (status === 'complete')
    return (
      <span
        className={cn(base, 'bg-[var(--green)]')}
        aria-label="Complete"
        title="Complete"
      />
    )
  if (status === 'failed')
    return (
      <span className={cn(base, 'bg-[var(--red)]')} aria-label="Failed" title="Failed" />
    )
  if (status === 'partial')
    return (
      <span className={cn(base, 'bg-[var(--yellow)]')} aria-label="Partial" title="Partial" />
    )
  if (status === 'running')
    return (
      <span
        className={cn(base, 'bg-[var(--accent)]')}
        style={{ animation: 'ds-pulse-dot 1.1s ease-in-out infinite' }}
        aria-label="Running"
        title="Running"
      />
    )
  return (
    <span
      className={cn(base, 'bg-[var(--textSubtle)]')}
      aria-label="Queued"
      title="Queued"
    />
  )
}

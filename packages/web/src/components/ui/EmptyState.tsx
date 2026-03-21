import type { ComponentType } from 'react'
import { Button } from '@/components/ui/Button'

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
}: {
  icon: ComponentType<{ className?: string; strokeWidth?: number }>
  title: string
  description: string
  actionLabel?: string
  onAction?: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center py-14 text-center">
      <Icon className="h-12 w-12 text-[var(--textSubtle)]" strokeWidth={1.25} aria-hidden />
      <h3 className="mt-4 font-display text-lg font-semibold text-[var(--text)]">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-[var(--textMuted)]">{description}</p>
      {actionLabel && onAction && (
        <Button type="button" className="mt-6" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  )
}

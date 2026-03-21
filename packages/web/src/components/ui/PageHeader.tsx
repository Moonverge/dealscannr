import { cn } from '@/lib/cn'

export function PageHeader({
  title,
  subtitle,
  actions,
  className,
}: {
  title: string
  subtitle?: string
  actions?: React.ReactNode
  className?: string
}) {
  return (
    <header
      className={cn(
        'mb-8 flex flex-col gap-4 border-b border-[var(--border)] pb-6 lg:flex-row lg:items-start lg:justify-between',
        className,
      )}
    >
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-[var(--text)] lg:text-[28px]">
          {title}
        </h1>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-[var(--textMuted)]">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  )
}

import { cn } from '@/lib/cn'

export function PageHeader({
  title,
  subtitle,
  actions,
  className,
  titleAs = 'h1',
}: {
  title: string
  subtitle?: string
  actions?: React.ReactNode
  className?: string
  /** Use `h2` when the page already has a primary `h1` (e.g. marketing hero). */
  titleAs?: 'h1' | 'h2'
}) {
  const TitleTag = titleAs === 'h2' ? 'h2' : 'h1'
  const titleClass =
    titleAs === 'h2'
      ? 'font-display text-xl font-semibold tracking-tight text-[var(--text)] lg:text-2xl'
      : 'font-display text-2xl font-semibold tracking-tight text-[var(--text)] lg:text-[28px]'

  return (
    <header
      className={cn(
        'mb-8 flex flex-col gap-4 border-b border-[var(--border)] pb-6 lg:flex-row lg:items-start lg:justify-between',
        className,
      )}
    >
      <div>
        <TitleTag className={titleClass}>{title}</TitleTag>
        {subtitle && <p className="mt-1 max-w-2xl text-sm text-[var(--textMuted)]">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  )
}

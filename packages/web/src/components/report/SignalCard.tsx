import type { Signal } from '@/types/report'

const sentimentStyles = {
  positive: 'border-l-[var(--green)] bg-[var(--positiveSoft)]',
  negative: 'border-l-[var(--red)] bg-[var(--negativeSoft)]',
  neutral: 'border-l-[var(--border)] bg-[var(--bg)]',
}

interface SignalCardProps {
  signal: Signal
  showCategoryBadge?: boolean
}

function formatCategory(cat: string): string {
  return cat.charAt(0).toUpperCase() + cat.slice(1)
}

export function SignalCard({ signal, showCategoryBadge = false }: SignalCardProps) {
  const sent = sentimentStyles[signal.sentiment] ?? sentimentStyles.neutral
  return (
    <article
      className={`rounded-sm border border-[var(--border)] border-l-4 ${sent} p-4 shadow-card`}
      data-category={signal.category}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-display font-medium text-[var(--text)]">
          {signal.title}
        </h3>
        {showCategoryBadge && (
          <span className="text-xs text-[var(--textMuted)] shrink-0">
            {formatCategory(signal.category)}
          </span>
        )}
      </div>
      <p className="mt-2 text-sm text-[var(--text)] leading-relaxed">
        {signal.description}
      </p>
      <footer className="mt-3 flex items-center gap-2 text-xs text-[var(--textMuted)]">
        <span>Source: {signal.source}</span>
        {signal.weight > 0 && (
          <span className="opacity-75">Weight: {signal.weight.toFixed(2)}</span>
        )}
      </footer>
    </article>
  )
}

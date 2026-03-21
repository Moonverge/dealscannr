import type { Verdict } from '@/types/report'

const styles: Record<Verdict, { bg: string; text: string; label: string }> = {
  green: { bg: 'bg-[var(--positiveSoft)]', text: 'text-[var(--green)]', label: 'Green' },
  yellow: { bg: 'bg-[var(--yellowSoft)]', text: 'text-[var(--yellow)]', label: 'Yellow' },
  red: { bg: 'bg-[var(--negativeSoft)]', text: 'text-[var(--red)]', label: 'Red' },
}

interface VerdictBadgeProps {
  verdict: Verdict
  confidence?: number
  className?: string
}

export function VerdictBadge({ verdict, confidence, className = '' }: VerdictBadgeProps) {
  const s = styles[verdict]
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-sm px-3 py-1.5 text-sm font-medium ${s.bg} ${s.text} ${className}`}
      title={confidence != null ? `Confidence: ${Math.round(confidence * 100)}%` : undefined}
    >
      <span className="font-display">{s.label}</span>
      {confidence != null && (
        <span className="opacity-80">{Math.round(confidence * 100)}%</span>
      )}
    </span>
  )
}

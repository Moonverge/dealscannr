import { cn } from '@/lib/cn'

type Size = 'sm' | 'md' | 'lg'

const dim: Record<Size, number> = { sm: 16, md: 24, lg: 40 }

export function Spinner({
  size = 'md',
  className,
  'aria-label': ariaLabel = 'Loading',
}: {
  size?: Size
  className?: string
  'aria-label'?: string
}) {
  const d = dim[size]
  const stroke = size === 'sm' ? 2.5 : size === 'md' ? 2.5 : 3
  return (
    <svg
      width={d}
      height={d}
      viewBox={`0 0 ${d} ${d}`}
      className={cn('ds-spinner text-[var(--accent)]', className)}
      aria-label={ariaLabel}
      role="status"
    >
      <circle
        cx={d / 2}
        cy={d / 2}
        r={d / 2 - stroke}
        fill="none"
        stroke="currentColor"
        strokeWidth={stroke}
        strokeDasharray={`${0.65 * Math.PI * (d - stroke * 2)} ${Math.PI * (d - stroke * 2)}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${d / 2} ${d / 2})`}
      />
    </svg>
  )
}

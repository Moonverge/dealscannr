import { cn } from '@/lib/cn'

type Padding = 'sm' | 'md' | 'lg' | 'none'

const pad: Record<Padding, string> = {
  sm: 'p-3',
  md: 'p-5',
  lg: 'p-7',
  none: 'p-0',
}

export function Card({
  children,
  hover = false,
  padding = 'md',
  className,
  ...rest
}: React.HTMLAttributes<HTMLDivElement> & {
  hover?: boolean
  padding?: Padding
}) {
  return (
    <div
      className={cn(
        'rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-dsSm',
        hover &&
          'transition-all duration-150 hover:-translate-y-px hover:shadow-dsMd active:scale-[0.99] active:duration-100',
        pad[padding],
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  )
}

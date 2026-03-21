import { cn } from '@/lib/cn'
import { Spinner } from '@/components/ui/Spinner'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant
  size?: Size
  loading?: boolean
  children: React.ReactNode
}

const sizeClasses: Record<Size, string> = {
  sm: 'min-h-8 px-3 text-sm rounded-[var(--radius-sm)]',
  md: 'min-h-10 px-4 text-sm rounded-[var(--radius-md)]',
  lg: 'min-h-12 px-5 text-base rounded-[var(--radius-md)]',
}

const variantClasses: Record<Variant, string> = {
  primary:
    'bg-[var(--accent)] text-white shadow-dsSm hover:bg-[var(--accentHover)] hover:shadow-dsMd active:scale-[0.98]',
  secondary:
    'border border-[var(--border)] bg-[var(--surface2)] text-[var(--text)] hover:bg-[var(--surface3)] active:scale-[0.98]',
  ghost: 'text-[var(--text)] hover:bg-[var(--surface2)] active:scale-[0.98]',
  danger: 'bg-[var(--red)] text-white hover:opacity-95 active:scale-[0.98]',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  className,
  children,
  type = 'button',
  ...rest
}: ButtonProps) {
  const isDisabled = disabled || loading
  return (
    <button
      type={type}
      disabled={isDisabled}
      className={cn(
        'inline-flex items-center justify-center gap-2 font-medium transition-all duration-150',
        'disabled:cursor-not-allowed disabled:opacity-45 disabled:active:scale-100',
        'hover:-translate-y-px disabled:hover:translate-y-0',
        sizeClasses[size],
        variantClasses[variant],
        loading && 'min-w-[7rem]',
        className,
      )}
      {...rest}
    >
      {loading ? (
        <>
          <Spinner size="sm" className="text-current" />
          <span className="sr-only">Loading</span>
        </>
      ) : (
        children
      )}
    </button>
  )
}

import { cn } from '@/lib/cn'

type Size = 'sm' | 'md' | 'lg'

const heights: Record<Size, string> = {
  sm: 'h-8 text-sm',
  md: 'h-10 text-sm',
  lg: 'h-12 text-base',
}

export type InputProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> & {
  label: string
  id: string
  size?: Size
  error?: string | null
  helperText?: string | null
  endAdornment?: React.ReactNode
}

export function Input({
  label,
  id,
  size = 'md',
  error,
  helperText,
  endAdornment,
  className,
  disabled,
  ...rest
}: InputProps) {
  return (
    <div className="w-full">
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-[var(--text)]">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          disabled={disabled}
          className={cn(
            'w-full rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3',
            'text-[var(--text)] outline-none transition-shadow',
            'placeholder:text-[var(--textSubtle)]',
            'focus:border-[var(--accent)] focus:shadow-[0_0_0_3px_var(--accentSoft)]',
            'disabled:cursor-not-allowed disabled:opacity-50',
            error &&
              'border-[var(--red)] focus:border-[var(--red)] focus:shadow-[0_0_0_3px_var(--negativeSoft)]',
            endAdornment ? 'pr-10' : undefined,
            heights[size],
            className,
          )}
          aria-invalid={error ? true : undefined}
          aria-describedby={
            error ? `${id}-err` : helperText ? `${id}-help` : undefined
          }
          {...rest}
        />
        {endAdornment ? (
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
            <div className="pointer-events-auto">{endAdornment}</div>
          </div>
        ) : null}
      </div>
      {error && (
        <p id={`${id}-err`} className="mt-1.5 text-sm text-[var(--red)]" role="alert">
          {error}
        </p>
      )}
      {!error && helperText && (
        <p id={`${id}-help`} className="mt-1.5 text-sm text-[var(--textMuted)]">
          {helperText}
        </p>
      )}
    </div>
  )
}

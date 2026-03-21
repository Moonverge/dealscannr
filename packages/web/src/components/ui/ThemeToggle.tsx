import { Moon, Sun } from 'lucide-react'
import { cn } from '@/lib/cn'
import { useThemeStore } from '@/stores/themeStore'

type Props = { className?: string; compact?: boolean }

export function ThemeToggle({ className, compact }: Props) {
  const theme = useThemeStore((s) => s.theme)
  const toggleTheme = useThemeStore((s) => s.toggleTheme)
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      onClick={() => toggleTheme()}
      className={cn(
        'inline-flex items-center justify-center rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] text-[var(--textMuted)] transition-colors hover:border-[var(--accentBorder)] hover:bg-[var(--surface2)] hover:text-[var(--text)]',
        compact ? 'h-8 w-8' : 'h-9 w-9',
        className,
      )}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Light mode' : 'Dark mode'}
    >
      {isDark ? <Sun className="h-4 w-4" strokeWidth={2} aria-hidden /> : <Moon className="h-4 w-4" strokeWidth={2} aria-hidden />}
    </button>
  )
}

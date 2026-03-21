import { useState, useCallback } from 'react'
import { useSearch } from '@/hooks/useSearch'

interface SearchBarProps {
  value: string
  onChange: (v: string) => void
  onSearch?: (q: string) => void
  placeholder?: string
  className?: string
}

export function SearchBar({
  value,
  onChange,
  onSearch,
  placeholder = 'Company name or natural language query…',
  className = '',
}: SearchBarProps) {
  const [local, setLocal] = useState(value)
  const { search, isSearching, error } = useSearch()

  const q = value !== undefined ? value : local
  const setQ = useCallback(
    (v: string) => {
      if (value === undefined) setLocal(v)
      onChange(v)
    },
    [value, onChange],
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = (value !== undefined ? value : local).trim()
    if (!trimmed) return
    onSearch?.(trimmed)
    search(trimmed)
  }

  return (
    <form onSubmit={handleSubmit} className={className}>
      <div className="flex gap-2 rounded-sm overflow-hidden border border-[var(--border)] bg-[var(--surface)] shadow-card focus-within:ring-2 focus-within:ring-[var(--accent)] focus-within:border-[var(--accent)]">
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={placeholder}
          disabled={isSearching}
          className="flex-1 min-w-0 px-4 py-3.5 text-[var(--text)] placeholder:text-[var(--textMuted)] bg-transparent border-0 focus:ring-0 focus:outline-none text-base"
          autoFocus
          aria-label="Company name or query"
        />
        <button
          type="submit"
          disabled={isSearching || !(q || '').trim()}
          className="px-6 py-3.5 bg-[var(--accent)] text-white font-medium rounded-r-sm hover:bg-[var(--accentHover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
        >
          {isSearching ? 'Scanning…' : 'Scan'}
        </button>
      </div>
      {isSearching && (
        <p className="mt-2 text-sm text-[var(--textMuted)]" role="status">
          Building intelligence report…
        </p>
      )}
      {error && (
        <p className="mt-2 text-sm text-[var(--red)]" role="alert">
          {error instanceof Error ? error.message : 'Search failed. Try again.'}
        </p>
      )}
    </form>
  )
}

interface SourceListProps {
  sources: string[]
  rawChunksCount?: number
}

export function SourceList({ sources, rawChunksCount }: SourceListProps) {
  if (sources.length === 0 && (rawChunksCount == null || rawChunksCount === 0)) {
    return null
  }

  return (
    <aside className="rounded-sm border border-[var(--border)] bg-[var(--surface)] p-4 shadow-card">
      <h3 className="font-display text-sm font-semibold text-[var(--text)] mb-2">
        Sources used
      </h3>
      <ul className="text-sm text-[var(--textMuted)] space-y-1 list-disc list-inside">
        {sources.length > 0 ? (
          sources.map((s, i) => (
            <li key={i}>{s}</li>
          ))
        ) : (
          <li>Raw chunks: {rawChunksCount ?? 0}</li>
        )}
      </ul>
    </aside>
  )
}

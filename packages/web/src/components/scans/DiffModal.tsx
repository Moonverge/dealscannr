type DiffChanges = Record<string, { new_chunks: number; summary: string }>

export type ScanDiffPayload = {
  new_scan_id: string
  previous_scan_id: string
  entity_name: string
  verdict_changed: boolean
  verdict_before: string
  verdict_after: string
  changes: DiffChanges
  notable_changes: string[]
}

type Props = {
  open: boolean
  loading: boolean
  error: string | null
  data: ScanDiffPayload | null
  onClose: () => void
}

export function DiffModal({ open, loading, error, data, onClose }: Props) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--overlay)] px-4 py-8">
      <div className="max-h-[90vh] w-full max-w-lg overflow-auto rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6 shadow-card">
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 className="text-sm font-semibold text-[var(--accent)]">Scan comparison</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-[var(--textMuted)] underline hover:text-[var(--text)]"
          >
            Close
          </button>
        </div>

        {loading && <p className="text-sm text-[var(--textMuted)]">Loading diff…</p>}
        {error && <p className="text-sm text-[var(--red)]">{error}</p>}

        {data && (
          <div className="space-y-4 text-sm">
            {data.entity_name && <p className="text-[var(--text)]">{data.entity_name}</p>}
            {data.verdict_changed && (
              <div className="rounded border border-[var(--yellow)]/40 bg-[var(--yellowSoft)] px-3 py-2 font-mono text-xs text-[var(--yellow)]">
                Verdict changed: {data.verdict_before} → {data.verdict_after}
              </div>
            )}
            <div className="space-y-2">
              {Object.entries(data.changes).map(([lane, c]) => (
                <div key={lane} className="rounded border border-[var(--border)] bg-[var(--bg)] px-3 py-2">
                  <span className="text-xs font-semibold capitalize text-[var(--accent)]">{lane}</span>
                  <p className="text-xs text-[var(--textMuted)]">
                    +{c.new_chunks} new sources — {c.summary}
                  </p>
                </div>
              ))}
            </div>
            {data.notable_changes.length > 0 && (
              <div>
                <h3 className="mb-2 text-xs font-medium text-[var(--textMuted)]">Notable changes</h3>
                <ul className="list-disc space-y-1 pl-5 text-[var(--text)]">
                  {data.notable_changes.map((line, i) => (
                    <li key={i}>{line}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

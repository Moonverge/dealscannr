import type { EntityCandidate } from '@/hooks/api/types'

type Props = {
  open: boolean
  onClose: () => void
  candidates: EntityCandidate[]
  confidence: number
  busy: boolean
  manualDomain: string
  onManualDomainChange: (v: string) => void
  onPickCandidate: (c: EntityCandidate) => void
  onConfirmManual: () => void
}

export function ResolveEntityModal({
  open,
  onClose,
  candidates,
  confidence,
  busy,
  manualDomain,
  onManualDomainChange,
  onPickCandidate,
  onConfirmManual,
}: Props) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--overlay)] px-4">
      <div className="max-h-[90vh] w-full max-w-md overflow-auto rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6 shadow-card">
        <h2 className="mb-4 text-lg font-semibold">Pick the right company</h2>
        <p className="mb-4 text-xs text-[var(--textMuted)]">
          Confidence {Math.round(confidence * 100)}% — choose a match or enter a domain.
        </p>
        <ul className="mb-4 space-y-2">
          {candidates.map((c, i) => (
            <li key={i}>
              <button
                type="button"
                disabled={busy}
                onClick={() => onPickCandidate(c)}
                className="w-full rounded border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-left text-sm text-[var(--text)] hover:border-[var(--accent)]"
              >
                <span className="font-medium">{c.legal_name}</span>
                <span className="block font-mono text-xs text-[var(--textMuted)]">
                  {c.domain || 'no domain'} · {Math.round(c.confidence * 100)}%
                </span>
              </button>
            </li>
          ))}
        </ul>
        <p className="mb-2 text-xs text-[var(--textMuted)]">None of these</p>
        <div className="flex gap-2">
          <input
            className="flex-1 rounded border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--text)] placeholder:text-[var(--textMuted)]"
            placeholder="manual domain"
            value={manualDomain}
            onChange={(e) => onManualDomainChange(e.target.value)}
          />
          <button
            type="button"
            disabled={busy || !manualDomain.trim()}
            onClick={onConfirmManual}
            className="rounded bg-[var(--accent)] px-3 py-2 text-sm font-medium text-white hover:bg-[var(--accentHover)] disabled:opacity-50"
          >
            Confirm
          </button>
        </div>
        <button
          type="button"
          className="mt-4 text-sm text-[var(--textMuted)] underline hover:text-[var(--text)]"
          onClick={onClose}
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

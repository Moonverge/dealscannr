import { Link, useParams } from 'react-router-dom'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { useSharedReportQuery } from '@/hooks/api/share.hooks'
import {
  mergeCitationDisplayOrder,
  normalizeChunkIdRefs,
} from '@/lib/chunk-citations'

const VERDICT_COLORS: Record<string, string> = {
  MEET: 'text-[var(--green)]',
  PASS: 'text-[var(--yellow)]',
  FLAG: 'text-[var(--red)]',
  INSUFFICIENT: 'text-[var(--textMuted)]',
}

export function SharedReport() {
  const { token } = useParams<{ token: string }>()
  const { data, isLoading, error } = useSharedReportQuery(token)

  if (isLoading) {
    return (
      <main className="min-h-screen bg-[var(--bg)] px-6 py-12 text-[var(--text)]">
        <p className="text-sm text-[var(--textMuted)]">Loading shared report…</p>
      </main>
    )
  }

  if (error || !data?.report) {
    return (
      <main className="min-h-screen bg-[var(--bg)] px-6 py-12 text-[var(--text)]">
        <p className="text-sm text-[var(--red)]">This link is invalid or has expired.</p>
        <Link to="/" className="mt-4 inline-block text-[var(--accent)] underline hover:text-[var(--accentHover)]">
          Home
        </Link>
      </main>
    )
  }

  const r = data.report
  const vclass = VERDICT_COLORS[r.verdict] || 'text-[var(--text)]'

  return (
    <main className="relative min-h-screen bg-[var(--bg)] px-6 py-12 pb-24 text-[var(--text)]">
      <div className="absolute right-4 top-4 sm:right-6 sm:top-6">
        <ThemeToggle compact />
      </div>
      <p className="mb-2 font-display text-sm font-semibold text-[var(--accent)]">Shared report</p>
      <p className="mb-4 text-sm text-[var(--textMuted)]">
        {data.entity_name}
        <span className="mx-2 text-[var(--border)]">·</span>
        <span className="font-mono text-xs">{data.scan_date}</span>
      </p>
      <div className="mb-6 flex flex-wrap items-center gap-4">
        {r.risk_triage ? (
          <span className="rounded-full border border-[var(--border)] bg-[var(--surface2)] px-3 py-1 text-xs font-medium text-[var(--textMuted)]">
            Risk:{' '}
            {r.risk_triage === 'clean'
              ? 'No material risks found'
              : r.risk_triage === 'watch'
                ? 'Signals worth monitoring'
                : r.risk_triage === 'flag'
                  ? 'Material adverse signals'
                  : 'Insufficient data to assess'}
          </span>
        ) : null}
        <h1 className={`text-2xl font-bold ${vclass}`}>{r.verdict}</h1>
        <span className="font-mono text-xs text-[var(--textMuted)]">
          {r.lane_coverage ?? 0}/4 lanes · {r.chunk_count ?? 0} chunks
          {r.confidence_score != null && (
            <> · conf {r.confidence_score.toFixed(2)}</>
          )}
        </span>
      </div>

      {(() => {
        const pq = (r.probe_questions ?? []).map((s) => s.trim()).filter(Boolean).slice(0, 3)
        if (!pq.length) return null
        const execCites = r.sections?.executive_summary?.citations ?? []
        const displayCites = mergeCitationDisplayOrder(execCites, pq)
        const pqNorm = pq.map((q) => normalizeChunkIdRefs(q, displayCites))
        const probesHaveNumericCites = /\[\d+\]/.test(pqNorm.join(''))
        return (
          <div className="mb-6 max-w-3xl rounded border border-[var(--border)] bg-[var(--surface)] p-4 shadow-card">
            <h3 className="mb-2 text-sm font-semibold text-[var(--accent)]">Before the call, probe</h3>
            <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--text)]">
              {pqNorm.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ul>
            {probesHaveNumericCites && displayCites.length > 0 ? (
              <ol className="mt-3 space-y-1 border-t border-[var(--border)] pt-3 font-mono text-[10px] text-[var(--textMuted)]">
                {displayCites.map((c, i) => (
                  <li key={i}>
                    [{i + 1}] {c}
                  </li>
                ))}
              </ol>
            ) : null}
          </div>
        )
      })()}

      <div className="max-w-3xl space-y-4">
        {Object.entries(r.sections || {}).map(([key, sec]) => (
          <section key={key} className="rounded border border-[var(--border)] bg-[var(--surface)] p-4 shadow-card">
            <h2 className="mb-2 text-sm font-semibold capitalize text-[var(--accent)]">
              {key.replace(/_/g, ' ')} · {sec.status}
            </h2>
            <p className="whitespace-pre-wrap text-sm text-[var(--text)]">
              {normalizeChunkIdRefs(sec.text ?? '', sec.citations ?? [])}
            </p>
            {sec.citations?.length > 0 && (
              <p className="mt-2 font-mono text-[10px] text-[var(--textMuted)]">
                Citations: {sec.citations.join(', ')}
              </p>
            )}
          </section>
        ))}
      </div>

      {r.known_unknowns?.length > 0 && (
        <div className="mt-8 max-w-3xl rounded border border-[var(--border)] bg-[var(--surface)] p-4 shadow-card">
          <h3 className="mb-2 text-sm font-semibold text-[var(--yellow)]">Known unknowns</h3>
          <ul className="list-disc pl-5 text-sm text-[var(--textMuted)]">
            {r.known_unknowns.map((u, i) => (
              <li key={i}>{u}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="mt-8 max-w-3xl text-xs text-[var(--textMuted)]">{r.disclaimer}</p>

      <footer className="fixed bottom-0 left-0 right-0 border-t border-[var(--border)] bg-[var(--surface)] px-6 py-4 text-center text-sm text-[var(--textMuted)] shadow-[0_-4px_24px_rgb(15_23_42/0.06)]">
        Powered by{' '}
        <span className="font-display font-semibold text-[var(--accent)]">DealScannr</span>
        <span className="mx-2 text-[var(--border)]">·</span>
        <Link to="/login" className="text-[var(--accent)] underline hover:text-[var(--accentHover)]">
          Sign up to run your own scans
        </Link>
      </footer>
    </main>
  )
}

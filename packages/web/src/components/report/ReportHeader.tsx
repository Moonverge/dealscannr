import { VerdictBadge } from './VerdictBadge'
import { formatCompanyDisplayName } from '@/lib/format-company-name'
import type { IntelligenceReport } from '@/types/report'

interface ReportHeaderProps {
  report: IntelligenceReport
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export function ReportHeader({ report }: ReportHeaderProps) {
  return (
    <header className="border-b border-[var(--border)] bg-[var(--surface)]">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl sm:text-3xl font-semibold text-[var(--text)] tracking-tight">
              {formatCompanyDisplayName(report.company_name)}
            </h1>
            <p className="text-sm text-[var(--textMuted)] mt-1">
              Report generated {formatDate(report.generated_at)}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            {report.raw_chunks_count === 0 && (
              <span className="rounded-sm border border-[var(--border)] bg-[var(--bg)] px-2 py-0.5 text-xs font-medium text-[var(--textMuted)]">
                Preliminary
              </span>
            )}
            <VerdictBadge verdict={report.verdict} confidence={report.confidence} />
          </div>
        </div>
        {report.raw_chunks_count === 0 && (
          <div
            className="mt-4 max-w-3xl rounded-sm border border-[var(--noticeBorder)] bg-[var(--noticeBg)] px-3 py-2 text-sm text-[var(--noticeText)]"
            role="status"
          >
            <strong className="font-medium">No Qdrant index for this company.</strong>{' '}
            {report.sources_used.length > 0
              ? 'Report may use a live web snapshot (see Sources used). Ingestion still required for primary-source DD.'
              : 'Add FIRECRAWL_API_KEY for richer live search, or run ingestion for indexed signals.'}
          </div>
        )}
        {report.summary && (
          <p className="mt-6 text-[var(--text)] leading-relaxed max-w-3xl">
            {report.summary}
          </p>
        )}
      </div>
    </header>
  )
}

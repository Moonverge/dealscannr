import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useReport } from '@/hooks/useReport'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { SearchBar } from '@/components/search/SearchBar'
import { ReportHeader } from '@/components/report/ReportHeader'
import { SignalGrid } from '@/components/report/SignalGrid'
import { SourceList } from '@/components/report/SourceList'

export function Report() {
  const { report, companyNameFromSlug } = useReport()
  const [searchInput, setSearchInput] = useState('')

  if (!report) {
    return (
      <div className="min-h-screen flex flex-col bg-[var(--bg)]">
        <header className="border-b border-[var(--border)] bg-[var(--surface)]">
          <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4 sm:px-6">
            <Link to="/" className="font-display text-lg font-semibold text-[var(--text)]">
              DEALSCANNR
            </Link>
            <ThemeToggle compact />
          </div>
        </header>
        <main className="flex-1 max-w-2xl mx-auto px-4 py-16 w-full">
          <h1 className="font-display text-2xl font-semibold text-[var(--text)] mb-2">
            No report loaded
          </h1>
          <p className="text-[var(--textMuted)] mb-6">
            Search for a company above to generate an intelligence report, or run a new search for
            {companyNameFromSlug ? ` "${companyNameFromSlug}".` : '.'}
          </p>
          <SearchBar
            value={searchInput}
            onChange={setSearchInput}
            onSearch={(q) => setSearchInput(q)}
            placeholder="Company name…"
          />
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg)]">
      <header className="border-b border-[var(--border)] bg-[var(--surface)]">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-3 px-4 py-4 sm:px-6">
          <Link to="/" className="font-display text-lg font-semibold text-[var(--text)]">
            DEALSCANNR
          </Link>
          <div className="flex items-center gap-2">
            <ThemeToggle compact />
            <Link
              to="/"
              className="text-sm font-medium text-[var(--accent)] hover:text-[var(--accentHover)]"
            >
              New search
            </Link>
          </div>
        </div>
      </header>

      <ReportHeader report={report} />

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_240px] gap-8">
          <div>
            <SignalGrid signals={report.signals} />
          </div>
          <div className="lg:sticky lg:top-6 lg:self-start">
            <SourceList
              sources={report.sources_used}
              rawChunksCount={report.raw_chunks_count}
            />
          </div>
        </div>
      </main>

      <footer className="border-t border-[var(--border)] py-6 text-center text-sm text-[var(--textMuted)]">
        dealscannr.com
      </footer>
    </div>
  )
}

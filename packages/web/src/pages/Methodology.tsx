import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { PublicLayout } from '@/components/layout/PublicLayout'
import { Card } from '@/components/ui/Card'
import { VerdictBadge } from '@/components/ui/Badge'
import { cn } from '@/lib/cn'

const SECTIONS = [
  { id: 'verdicts', label: 'Verdicts' },
  { id: 'sources', label: 'Data sources' },
  { id: 'limitations', label: 'Limitations' },
  { id: 'hallucination', label: 'Hallucination controls' },
  { id: 'disclaimer', label: 'Disclaimer' },
] as const

const SOURCE_CARDS = [
  {
    name: 'SEC EDGAR',
    desc: 'Federal securities disclosures and material events.',
    fresh: 'Last 12 months of filings',
    icon: '📄',
  },
  {
    name: 'CourtListener',
    desc: 'Federal court dockets and opinions where indexed.',
    fresh: 'Historical — federal',
    icon: '⚖',
  },
  {
    name: 'GitHub',
    desc: 'Public repository and organization activity.',
    fresh: 'Last 52 weeks',
    icon: '⚙',
  },
  {
    name: 'Job boards',
    desc: 'Posted roles and hiring mix signals.',
    fresh: 'Current listings',
    icon: '👥',
  },
  {
    name: 'News',
    desc: 'Recent coverage and web baseline.',
    fresh: 'Last 30 days',
    icon: '📰',
  },
] as const

export function Methodology() {
  useEffect(() => {
    document.title = 'Methodology — DealScannr'
  }, [])

  return (
    <PublicLayout>
      <div className="mx-auto flex max-w-5xl gap-10 px-4 py-12 lg:py-16">
        <aside className="sticky top-24 hidden w-48 shrink-0 self-start lg:block">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--textSubtle)]">On this page</p>
          <nav className="mt-4 space-y-1 text-sm" aria-label="Section">
            {SECTIONS.map((s) => (
              <a
                key={s.id}
                href={`#${s.id}`}
                className="block rounded-[var(--radius-sm)] px-2 py-1.5 text-[var(--textMuted)] hover:bg-[var(--surface2)] hover:text-[var(--accent)]"
              >
                {s.label}
              </a>
            ))}
          </nav>
        </aside>

        <article className="min-w-0 max-w-[720px] flex-1">
          <h1 className="font-display text-3xl font-semibold text-[var(--text)]">Methodology</h1>
          <p className="mt-3 text-[var(--textMuted)]">
            How we score verdicts, where data comes from, and what we refuse to guess.
          </p>

          <div className="mt-8 space-y-2 border-y border-[var(--border)] py-4 lg:hidden">
            <p className="text-xs font-semibold uppercase text-[var(--textSubtle)]">Jump to</p>
            <div className="flex flex-wrap gap-2">
              {SECTIONS.map((s) => (
                <a
                  key={s.id}
                  href={`#${s.id}`}
                  className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-xs text-[var(--text)]"
                >
                  {s.label}
                </a>
              ))}
            </div>
          </div>

          <section id="verdicts" className="scroll-mt-28 border-b border-[var(--border)] py-12">
            <h2 className="font-display text-xl font-semibold text-[var(--text)]">How verdicts are scored</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--textMuted)]">
              The model assigns one headline verdict per scan using a fixed rubric. Wording inside the memo may
              vary; categories map as follows.
            </p>
            <div className="mt-6 overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--border)] shadow-dsSm">
              <table className="w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] bg-[var(--surface2)] text-xs font-semibold uppercase text-[var(--textSubtle)]">
                    <th className="p-3">Verdict</th>
                    <th className="p-3">Meaning</th>
                  </tr>
                </thead>
                <tbody className="bg-[var(--surface)] text-[var(--text)]">
                  <tr className="border-b border-[var(--border)]">
                    <td className="p-3 align-top">
                      <VerdictBadge verdict="FLAG" size="sm" />
                    </td>
                    <td className="p-3 text-[var(--textMuted)]">
                      Active litigation or regulatory enforcement signals in retrieved evidence.
                    </td>
                  </tr>
                  <tr className="border-b border-[var(--border)]">
                    <td className="p-3 align-top">
                      <VerdictBadge verdict="MEET" size="sm" />
                    </td>
                    <td className="p-3 text-[var(--textMuted)]">
                      Positive signals in two or more lanes; no FLAG conditions triggered.
                    </td>
                  </tr>
                  <tr className="border-b border-[var(--border)]">
                    <td className="p-3 align-top">
                      <VerdictBadge verdict="PASS" size="sm" />
                    </td>
                    <td className="p-3 text-[var(--textMuted)]">
                      Material data found, but no strong positive pattern across lanes.
                    </td>
                  </tr>
                  <tr>
                    <td className="p-3 align-top">
                      <VerdictBadge verdict="INSUFFICIENT" size="sm" />
                    </td>
                    <td className="p-3 text-[var(--textMuted)]">
                      Fewer than two connector lanes returned usable data.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section id="sources" className="scroll-mt-28 border-b border-[var(--border)] py-12">
            <h2 className="font-display text-xl font-semibold text-[var(--text)]">Data sources</h2>
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              {SOURCE_CARDS.map((s) => (
                <Card key={s.name} padding="md" className="flex gap-3">
                  <span className="text-2xl" aria-hidden>
                    {s.icon}
                  </span>
                  <div>
                    <h3 className="font-display font-semibold text-[var(--text)]">{s.name}</h3>
                    <p className="mt-1 text-sm text-[var(--textMuted)]">{s.desc}</p>
                    <span
                      className={cn(
                        'mt-2 inline-block rounded-full border border-[var(--border)] bg-[var(--surface2)] px-2 py-0.5 font-mono text-[10px] text-[var(--textMuted)]',
                      )}
                    >
                      {s.fresh}
                    </span>
                  </div>
                </Card>
              ))}
            </div>
          </section>

          <section id="limitations" className="scroll-mt-28 border-b border-[var(--border)] py-12">
            <h2 className="font-display text-xl font-semibold text-[var(--text)]">Known limitations</h2>
            <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-[var(--textMuted)]">
              <li>Private companies are assessed from public signals only; coverage may be sparse.</li>
              <li>Federal court emphasis — many state-court matters may not appear.</li>
              <li>GitHub signals require discoverable public orgs or repos tied to the domain.</li>
              <li>Hiring lanes reflect postings, not verified headcount.</li>
              <li>Each report is a snapshot — rescan before material decisions.</li>
            </ul>
          </section>

          <section id="hallucination" className="scroll-mt-28 border-b border-[var(--border)] py-12">
            <h2 className="font-display text-xl font-semibold text-[var(--text)]">Hallucination controls</h2>
            <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-[var(--textMuted)]">
              <li>Grounding contract enforced in synthesis prompts — claims must tie to chunk ids.</li>
              <li>Low temperature for factual JSON outputs.</li>
              <li>Known unknowns and lane status disclosed when connectors fail or return partial data.</li>
            </ul>
          </section>

          <section id="disclaimer" className="scroll-mt-28 py-12">
            <h2 className="font-display text-xl font-semibold text-[var(--text)]">Disclaimer</h2>
            <p className="mt-4 text-[13px] leading-relaxed text-[var(--textSubtle)]">
              DealScannr provides automated research assistance based on third-party and public data. It is not
              legal, financial, or investment advice. Outputs may be incomplete, outdated, or incorrect. You are
              responsible for verifying all material facts and consulting qualified professionals before relying on
              any report. Use of the service is at your own risk; we disclaim liability to the fullest extent permitted
              by law.
            </p>
          </section>

          <Link to="/" className="inline-block text-sm font-medium text-[var(--accent)] underline">
            ← Home
          </Link>
        </article>
      </div>
    </PublicLayout>
  )
}

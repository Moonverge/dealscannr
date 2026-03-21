import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/cn'

export type FaqItem = { q: string; a: string }

const DEFAULT_FAQ: FaqItem[] = [
  {
    q: 'What does a verdict mean?',
    a: 'MEET, PASS, FLAG, and INSUFFICIENT map to a fixed rubric described in our Methodology. Each reflects patterns across litigation, engineering, hiring, and news lanes — not a buy/sell recommendation.',
  },
  {
    q: 'How fresh is the data?',
    a: 'Windows vary by source (e.g. news ~30 days, SEC ~12 months). Each scan is a point-in-time snapshot — rescan before important decisions.',
  },
  {
    q: 'Do I need a contract?',
    a: 'No data contracts on standard plans. Subscribe monthly, cancel anytime.',
  },
  {
    q: 'Is this legal or investment advice?',
    a: 'No. DealScannr surfaces public signals and AI-synthesized summaries. You must verify facts and consult qualified professionals.',
  },
  {
    q: 'What happens if a lane fails?',
    a: 'We label lanes as Complete, Partial, or Insufficient and disclose gaps in “known unknowns” so you know what was not found.',
  },
]

export function FaqAccordion({ items = DEFAULT_FAQ }: { items?: FaqItem[] }) {
  const [open, setOpen] = useState<number | null>(0)

  return (
    <div className="divide-y divide-[var(--border)] rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] shadow-dsSm">
      {items.map((item, i) => {
        const isOpen = open === i
        return (
          <div key={i}>
            <button
              type="button"
              className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
              aria-expanded={isOpen}
              onClick={() => setOpen(isOpen ? null : i)}
            >
              <span className="font-display text-sm font-semibold text-[var(--text)]">{item.q}</span>
              <ChevronDown
                className={cn(
                  'h-5 w-5 shrink-0 text-[var(--textMuted)] transition-transform duration-200',
                  isOpen && 'rotate-180',
                )}
                aria-hidden
              />
            </button>
            <div
              className={cn(
                'grid transition-[grid-template-rows] duration-200 ease-out',
                isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]',
              )}
            >
              <div className="overflow-hidden">
                <p className="px-5 pb-4 text-sm leading-relaxed text-[var(--textMuted)]">{item.a}</p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

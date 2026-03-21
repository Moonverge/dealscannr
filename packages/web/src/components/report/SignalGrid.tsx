import { SignalCard } from './SignalCard'
import type { Signal } from '@/types/report'

const categoryOrder: Signal['category'][] = [
  'team',
  'founder',
  'legal',
  'engineering',
  'hiring',
  'product',
  'customer',
  'financials',
]

function groupByCategory(signals: Signal[]): Map<Signal['category'], Signal[]> {
  const map = new Map<Signal['category'], Signal[]>()
  for (const s of signals) {
    const list = map.get(s.category) ?? []
    list.push(s)
    map.set(s.category, list)
  }
  return map
}

function formatCategory(cat: string): string {
  return cat.charAt(0).toUpperCase() + cat.slice(1)
}

interface SignalGridProps {
  signals: Signal[]
}

export function SignalGrid({ signals }: SignalGridProps) {
  const byCategory = groupByCategory(signals)
  const order = categoryOrder.filter((c) => byCategory.has(c))
  const rest = [...byCategory.keys()].filter((c) => !categoryOrder.includes(c))

  if (signals.length === 0) {
    return (
      <p className="text-[var(--textMuted)] py-8 text-center">
        No signals in this report.
      </p>
    )
  }

  return (
    <div className="space-y-10">
      {[...order, ...rest].map((category) => {
        const list = byCategory.get(category) ?? []
        return (
          <section key={category}>
            <h2 className="font-display text-lg font-semibold text-[var(--text)] mb-3">
              {formatCategory(category)}
            </h2>
            <ul className="space-y-3 list-none p-0 m-0">
              {list.map((signal, i) => (
                <li key={`${signal.title}-${i}`}>
                  <SignalCard signal={signal} />
                </li>
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}

export type Verdict = 'green' | 'yellow' | 'red'

export type SignalCategory =
  | 'team'
  | 'legal'
  | 'engineering'
  | 'hiring'
  | 'customer'
  | 'financials'
  | 'founder'
  | 'product'

export type SignalSentiment = 'positive' | 'negative' | 'neutral'

export interface Signal {
  category: SignalCategory
  title: string
  description: string
  sentiment: SignalSentiment
  source: string
  date_detected: string | null
  weight: number
}

export interface IntelligenceReport {
  company_name: string
  generated_at: string
  verdict: Verdict
  confidence: number
  summary: string
  signals: Signal[]
  sources_used: string[]
  raw_chunks_count: number
}

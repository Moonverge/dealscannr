import { create } from 'zustand'
import type { IntelligenceReport } from '@/types/report'

interface ReportState {
  report: IntelligenceReport | null
  setReport: (r: IntelligenceReport | null) => void
}

export const useReportStore = create<ReportState>((set) => ({
  report: null,
  setReport: (report) => set({ report }),
}))

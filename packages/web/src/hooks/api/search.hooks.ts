import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import axiosInstance from '@/core/api/axios.instance'
import { SEARCH } from '@/core/api/routes'
import type { IntelligenceReport } from '@/types/report'
import { useReportStore } from '@/stores/reportStore'
import { useSearchStore } from '@/stores/searchStore'

function slug(name: string): string {
  return (
    name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '') || 'company'
  )
}

function normalizeQuery(q: string): string {
  let s = q.trim().slice(0, 200)
  const pairs: [string, string][] = [
    ['"', '"'],
    ["'", "'"],
    ['`', '`'],
    ['\u201c', '\u201d'],
  ]
  for (const [a, b] of pairs) {
    if (s.length >= 2 && s.startsWith(a) && s.endsWith(b)) {
      s = s.slice(1, -1).trim()
      break
    }
  }
  return s.replace(/^['"]+|['"]+$/g, '').trim()
}

/** Public search (home / report flow): POST /api/search */
export function useCompanySearchMutation() {
  const navigate = useNavigate()
  const setReport = useReportStore((s) => s.setReport)
  const setIsSearching = useSearchStore((s) => s.setIsSearching)

  return useMutation({
    mutationFn: async (query: string): Promise<IntelligenceReport> => {
      const q = normalizeQuery(query)
      const { data } = await axiosInstance.post<IntelligenceReport>(SEARCH.POST(), {
        query: q,
        company_name: q,
      })
      return data
    },
    onMutate: () => setIsSearching(true),
    onSettled: () => setIsSearching(false),
    onSuccess: (report) => {
      setReport(report)
      navigate(`/report/${slug(report.company_name)}`)
    },
  })
}

import { useParams } from 'react-router-dom'
import { useReportStore } from '@/stores/reportStore'

function slugFromName(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'company'
}

function slugToName(slug: string): string {
  return slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function useReport() {
  const { slug } = useParams<{ slug: string }>()
  const report = useReportStore((s) => s.report)
  const displayReport =
    report && slug && slugFromName(report.company_name) === slug ? report : null
  return {
    report: displayReport,
    slug: slug ?? '',
    companyNameFromSlug: slug ? slugToName(slug) : '',
  }
}

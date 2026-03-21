/**
 * Legacy barrel: prefer `@/core/api/axios.instance` and `@/core/api/routes` in new code.
 */
import { apiUrl, BASE_URL, COMPANIES, REPORTS, SEARCH } from '@/core/api/routes'

export { default as api } from '@/core/api/axios.instance'
export { BASE_URL, apiUrl, SEARCH, REPORTS, COMPANIES }

export function searchUrl(): string {
  return apiUrl(SEARCH.POST())
}

export function reportUrl(id: string): string {
  return apiUrl(REPORTS.BY_ID(id))
}

export function companyUrl(slug: string): string {
  return apiUrl(COMPANIES.BY_SLUG(slug))
}

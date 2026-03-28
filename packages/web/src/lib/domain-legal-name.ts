/** Match backend domain_to_legal_name for display / confirm payloads when user enters a domain only. */
export function domainStemTitleCase(domain: string): string {
  const raw = domain.trim()
  const d = raw
    .toLowerCase()
    .replace(/^https?:\/\//i, '')
    .split('/')[0]
    ?.split(':')[0] ?? ''
  const stem = d.split('.')[0] ?? ''
  if (stem.length < 2) return raw
  return stem.charAt(0).toUpperCase() + stem.slice(1).toLowerCase()
}

export function readScanMeta(scanId: string | undefined): { company: string; domain: string } | null {
  if (!scanId || typeof sessionStorage === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(`scan.${scanId}.meta`)
    if (!raw) return null
    const j = JSON.parse(raw) as { company?: string; domain?: string }
    return { company: j.company ?? '', domain: j.domain ?? '' }
  } catch {
    return null
  }
}

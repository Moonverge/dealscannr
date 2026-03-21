/**
 * Normalize model output that uses [chunk_id: <hex>] into numeric [1], [2], …
 * for the same citation list the API stores on each section.
 */

export function collectHexChunkIdsFromText(s: string): string[] {
  const out: string[] = []
  const re = /\[chunk_id:\s*([a-fA-F0-9]+)\]/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(s)) !== null) {
    out.push(m[1])
  }
  return out
}

/** Executive citations first (preserve order), then any chunk ids found in probe lines. */
export function mergeCitationDisplayOrder(base: string[], extraLines: string[]): string[] {
  const merged: string[] = []
  const seen = new Set<string>()
  for (const c of base) {
    const id = c?.trim()
    if (!id || seen.has(id)) continue
    seen.add(id)
    merged.push(id)
  }
  for (const line of extraLines) {
    for (const id of collectHexChunkIdsFromText(line)) {
      if (!seen.has(id)) {
        seen.add(id)
        merged.push(id)
      }
    }
  }
  return merged
}

export function normalizeChunkIdRefs(text: string, citations: string[]): string {
  let t = text
  for (let i = 0; i < citations.length; i++) {
    const cid = citations[i]?.trim()
    if (!cid) continue
    const esc = cid.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    t = t.replace(new RegExp(`\\[chunk_id:\\s*${esc}\\]`, 'gi'), `[${i + 1}]`)
  }
  return t
}

/** Decode JWT payload for display only (not verified). */
export function getEmailFromToken(token: string | null): string | null {
  if (!token) return null
  try {
    const part = token.split('.')[1]
    if (!part) return null
    const json = JSON.parse(
      globalThis.atob(part.replace(/-/g, '+').replace(/_/g, '/')),
    ) as Record<string, unknown>
    const email = json.email
    const sub = json.sub
    if (typeof email === 'string') return email
    if (typeof sub === 'string' && sub.includes('@')) return sub
    return typeof sub === 'string' ? sub : null
  } catch {
    return null
  }
}

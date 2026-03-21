export type VerdictKey = 'MEET' | 'PASS' | 'FLAG' | 'INSUFFICIENT' | 'PRELIMINARY'

export type VerdictStyleKey = VerdictKey | 'OTHER'

export function normalizeVerdict(v: string | null | undefined): VerdictStyleKey {
  const u = (v || '').toUpperCase().trim()
  if (u.includes('PRELIMINARY')) return 'PRELIMINARY'
  if (u.includes('MEET')) return 'MEET'
  if (u.includes('PASS')) return 'PASS'
  if (u.includes('FLAG')) return 'FLAG'
  if (u.includes('INSUFFICIENT')) return 'INSUFFICIENT'
  return 'OTHER'
}

export function verdictStyles(key: VerdictStyleKey): {
  color: string
  bg: string
  border: string
} {
  switch (key) {
    case 'MEET':
      return {
        color: 'var(--green)',
        bg: 'var(--positiveSoft)',
        border: 'rgb(5 150 105 / 0.35)',
      }
    case 'PASS':
      return {
        color: 'var(--yellow)',
        bg: 'var(--yellowSoft)',
        border: 'rgb(217 119 6 / 0.35)',
      }
    case 'FLAG':
      return {
        color: 'var(--red)',
        bg: 'var(--negativeSoft)',
        border: 'rgb(220 38 38 / 0.35)',
      }
    case 'INSUFFICIENT':
      return {
        color: 'var(--textMuted)',
        bg: 'var(--surface2)',
        border: 'var(--border)',
      }
    case 'PRELIMINARY':
      return {
        color: 'var(--preliminaryText)',
        bg: 'var(--preliminaryBg)',
        border: 'var(--preliminaryBorder)',
      }
    case 'OTHER':
    default:
      return {
        color: 'var(--textMuted)',
        bg: 'var(--surface2)',
        border: 'var(--border)',
      }
  }
}

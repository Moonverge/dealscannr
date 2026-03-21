export function formatCompanyDisplayName(name: string): string {
  const s = name.trim()
  if (!s) return s
  return s
    .split(/(\s+|[-/&])/)
    .map((part) => {
      if (/^\s+$/.test(part) || /^[-/&]$/.test(part)) return part
      if (!part) return part
      return part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()
    })
    .join('')
}

import axios from 'axios'

export type GuestTrialModalVariant = 'session' | 'exhausted' | 'ip_limit'

/** Map guest/trial API errors to modal variant; returns null for unrelated errors. */
export function guestTrialErrorFromAxios(error: unknown): GuestTrialModalVariant | null {
  if (!axios.isAxiosError(error)) return null
  const st = error.response?.status
  const data = error.response?.data as { error?: string } | undefined
  const code = data?.error
  if (st === 401 && (code === 'guest_session_required' || code === 'guest_session_invalid')) {
    return 'session'
  }
  if (st === 403 && code === 'guest_scan_exhausted') return 'exhausted'
  if (st === 403 && code === 'guest_ip_limit') return 'ip_limit'
  return null
}

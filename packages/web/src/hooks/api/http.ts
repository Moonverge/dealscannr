import axios from 'axios'

export function getAxiosStatus(error: unknown): number | undefined {
  return axios.isAxiosError(error) ? error.response?.status : undefined
}

export function getAxiosResponseMessage(error: unknown): string | undefined {
  if (!axios.isAxiosError(error)) return undefined
  const d = error.response?.data
  if (d && typeof d === 'object' && 'message' in d) {
    const m = (d as { message?: unknown }).message
    return typeof m === 'string' ? m : undefined
  }
  return undefined
}

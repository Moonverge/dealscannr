import { Navigate, useSearchParams } from 'react-router-dom'

/** Legacy `/try` URL: guest scan now lives on the home page. */
export function TryScan() {
  const [searchParams] = useSearchParams()
  const qs = searchParams.toString()
  return <Navigate to={qs ? `/?${qs}` : '/'} replace />
}

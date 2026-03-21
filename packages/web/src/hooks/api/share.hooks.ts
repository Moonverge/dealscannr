import { useQuery } from '@tanstack/react-query'
import axiosInstance from '@/core/api/axios.instance'
import { SHARE } from '@/core/api/routes'
import type { SharedReportPayload } from '@/hooks/api/types'

export function useSharedReportQuery(token: string | undefined) {
  return useQuery({
    queryKey: ['shared-report', token],
    enabled: Boolean(token),
    retry: 0,
    queryFn: async () => {
      const { data } = await axiosInstance.get<SharedReportPayload>(SHARE.PUBLIC_REPORT(token!))
      return data
    },
  })
}

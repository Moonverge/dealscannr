import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axiosInstance from '@/core/api/axios.instance'
import { BATCH } from '@/core/api/routes'
import type { BatchStatusPayload } from '@/hooks/api/types'

export function useBatchUploadMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      const { data } = await axiosInstance.post<{ batch_id: string; total: number; status: string }>(
        BATCH.UPLOAD(),
        fd,
        {
          transformRequest: (body, headers) => {
            if (body instanceof FormData) {
              delete headers['Content-Type']
            }
            return body as FormData
          },
        },
      )
      return data
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['credits'] })
    },
  })
}

export function useBatchStatusQuery(batchId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['batch-status', batchId],
    enabled: Boolean(batchId) && enabled,
    refetchInterval: (q) => {
      const st = q.state.data?.status
      return st === 'complete' || st === 'failed' ? false : 3000
    },
    queryFn: async () => {
      const { data } = await axiosInstance.get<BatchStatusPayload>(BATCH.STATUS(batchId!))
      return data
    },
  })
}

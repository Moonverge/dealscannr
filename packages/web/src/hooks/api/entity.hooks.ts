import { useMutation } from '@tanstack/react-query'
import axiosInstance from '@/core/api/axios.instance'
import { ENTITY } from '@/core/api/routes'
import type { EntityCandidate } from '@/hooks/api/types'

export function useResolveEntityMutation() {
  return useMutation({
    mutationFn: (body: { name: string; domain_hint?: string }) =>
      axiosInstance
        .post<{ candidates: EntityCandidate[]; confidence: number }>(ENTITY.RESOLVE(), body)
        .then((r) => r.data),
  })
}

export function useConfirmEntityMutation() {
  return useMutation({
    mutationFn: (body: {
      legal_name: string
      domain: string
      candidate_id?: string | null
    }) => axiosInstance.post<{ entity_id: string }>(ENTITY.CONFIRM(), body).then((r) => r.data),
  })
}

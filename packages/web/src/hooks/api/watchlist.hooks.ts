import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axiosInstance from '@/core/api/axios.instance'
import { WATCHLIST } from '@/core/api/routes'
import type { WatchlistEntry } from '@/hooks/api/types'

export function useWatchlistQuery(enabled: boolean) {
  return useQuery({
    queryKey: ['watchlist'],
    enabled,
    queryFn: async () => {
      const { data } = await axiosInstance.get<{ entries: WatchlistEntry[] }>(WATCHLIST.LIST())
      return data.entries ?? []
    },
  })
}

export function useAddWatchlistMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { entity_id: string; notify_on?: string[] }) =>
      axiosInstance.post<WatchlistEntry>(WATCHLIST.ADD(), body).then((r) => r.data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['watchlist'] })
    },
  })
}

export function usePatchWatchlistMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (args: { entityId: string; notify_on: string[] }) =>
      axiosInstance
        .patch<WatchlistEntry>(WATCHLIST.PATCH(args.entityId), { notify_on: args.notify_on })
        .then((r) => r.data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['watchlist'] })
    },
  })
}

export function useRemoveWatchlistMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (entityId: string) => axiosInstance.delete(WATCHLIST.REMOVE(entityId)),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['watchlist'] })
    },
  })
}

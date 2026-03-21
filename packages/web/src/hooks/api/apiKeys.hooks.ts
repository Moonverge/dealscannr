import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import axiosInstance from '@/core/api/axios.instance'
import { API_KEYS } from '@/core/api/routes'
import type { ApiKeyRow } from '@/hooks/api/types'

export function useApiKeysQuery(enabled: boolean) {
  return useQuery({
    queryKey: ['api-keys'],
    enabled,
    queryFn: async () => {
      const { data } = await axiosInstance.get<{ keys: ApiKeyRow[] }>(API_KEYS.LIST())
      return data.keys ?? []
    },
  })
}

export function useCreateApiKeyMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string; scopes?: string[] }) =>
      axiosInstance
        .post<{ key: string; prefix: string; name: string; scopes: string[]; created_at: string }>(
          API_KEYS.CREATE(),
          body,
        )
        .then((r) => r.data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['api-keys'] })
    },
  })
}

export function useDeleteApiKeyMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (prefix: string) => axiosInstance.delete(API_KEYS.DELETE(prefix)),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['api-keys'] })
    },
  })
}

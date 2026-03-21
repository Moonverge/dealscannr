import { useQuery } from '@tanstack/react-query'
import axiosInstance from '@/core/api/axios.instance'
import { USERS } from '@/core/api/routes'
import type { CreditsPayload } from '@/hooks/api/types'

export function useCreditsQuery(enabled: boolean) {
  return useQuery({
    queryKey: ['credits'],
    enabled,
    queryFn: async () => {
      const { data } = await axiosInstance.get<CreditsPayload>(USERS.ME_CREDITS())
      return data
    },
  })
}

export async function fetchCredits(): Promise<CreditsPayload> {
  const { data } = await axiosInstance.get<CreditsPayload>(USERS.ME_CREDITS())
  return data
}

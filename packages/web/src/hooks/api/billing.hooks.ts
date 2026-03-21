import { useMutation, useQuery } from '@tanstack/react-query'
import axiosInstance from '@/core/api/axios.instance'
import { BILLING } from '@/core/api/routes'
import type { BillingStatus } from '@/hooks/api/types'

export function useBillingCheckoutMutation() {
  return useMutation({
    mutationFn: (body: { plan: 'pro' | 'team' }) =>
      axiosInstance.post<{ checkout_url: string }>(BILLING.CHECKOUT(), body).then((r) => r.data),
  })
}

export function useBillingPortalMutation() {
  return useMutation({
    mutationFn: () =>
      axiosInstance.post<{ portal_url: string }>(BILLING.PORTAL()).then((r) => r.data),
  })
}

export async function fetchBillingStatus(): Promise<BillingStatus> {
  const { data } = await axiosInstance.get<BillingStatus>(BILLING.STATUS())
  return data
}

export function useBillingStatusQuery(enabled: boolean) {
  return useQuery({
    queryKey: ['billing-status'],
    enabled,
    queryFn: fetchBillingStatus,
  })
}

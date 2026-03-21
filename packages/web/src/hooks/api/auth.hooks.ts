import { useMutation } from '@tanstack/react-query'
import axiosInstance from '@/core/api/axios.instance'
import { AUTH } from '@/core/api/routes'

export function useLoginMutation() {
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      axiosInstance.post<{ token: string }>(AUTH.LOGIN(), body).then((r) => r.data),
  })
}

export function useRegisterMutation() {
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      axiosInstance.post<{ token: string }>(AUTH.REGISTER(), body).then((r) => r.data),
  })
}

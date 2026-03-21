import { useCompanySearchMutation } from '@/hooks/api/search.hooks'

export function useSearch() {
  const mutation = useCompanySearchMutation()
  return {
    search: mutation.mutate,
    isSearching: mutation.isPending,
    error: mutation.error,
    reset: mutation.reset,
  }
}

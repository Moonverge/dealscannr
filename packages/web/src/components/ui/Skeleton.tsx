import { cn } from '@/lib/cn'

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('ds-skeleton rounded-[var(--radius-sm)]', className)} aria-hidden />
}

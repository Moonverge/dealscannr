import { useLocation } from 'react-router-dom'
import { cn } from '@/lib/cn'

export function PageTransition({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  const { pathname } = useLocation()
  return (
    <div key={pathname} className={cn('ds-page-transition', className)}>
      {children}
    </div>
  )
}

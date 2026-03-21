import { useEffect } from 'react'
import { Link, matchPath, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Eye, LayoutDashboard, LogOut, Settings, Upload } from 'lucide-react'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { useCreditsQuery } from '@/hooks/api/users.hooks'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import { getEmailFromToken } from '@/lib/jwt-email'
import { cn } from '@/lib/cn'
import { useAuthStore } from '@/stores/authStore'
import { PageTransition } from '@/components/ui/PageTransition'

const nav = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/watchlist', label: 'Watchlist', icon: Eye },
  { to: '/batch', label: 'Batch', icon: Upload },
  { to: '/settings', label: 'Settings', icon: Settings },
] as const

/** Declarative routes only (BrowserRouter): match pathname, most specific first. */
const SHELL_ROUTE_META: {
  path: string
  title?: string
  hideTitle?: boolean
  a11yTitle?: string
}[] = [
  { path: '/scan/:scanId/report', hideTitle: true, a11yTitle: 'Intelligence report' },
  { path: '/scan/:scanId/progress', title: 'Scan progress' },
  { path: '/dashboard', title: 'Dashboard' },
  { path: '/watchlist', title: 'Watchlist' },
  { path: '/batch', title: 'Batch' },
  { path: '/settings', title: 'Settings' },
]

function shellMetaFromPathname(pathname: string) {
  for (const row of SHELL_ROUTE_META) {
    if (matchPath({ path: row.path, end: true }, pathname)) return row
  }
  return undefined
}

function CreditsBlock({ compact }: { compact?: boolean }) {
  const token = useAuthStore((s) => s.token)
  const { data: credits } = useCreditsQuery(Boolean(token))
  if (!credits) {
    return (
      <div
        className={cn(
          'rounded-[var(--radius-md)] bg-[var(--shellNavItemActiveTint)] p-3',
          compact && 'p-2',
        )}
      >
        <p className="text-xs text-[var(--textMuted)]">Loading credits…</p>
      </div>
    )
  }
  const usedPct = credits.monthly_limit
    ? Math.min(100, (credits.monthly_used / credits.monthly_limit) * 100)
    : 0
  const reset = new Date(credits.resets_at)
  const resetLabel = reset.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

  return (
    <div className="rounded-[var(--radius-md)] bg-[var(--shellNavItemActiveTint)] p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-[var(--text)]">
          {credits.monthly_used} of {credits.monthly_limit} scans
        </span>
        <span className="rounded border border-[var(--accentBorder)] bg-[var(--accentSoft)] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--accent)]">
          {credits.plan}
        </span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--surface3)]">
        <div
          className="h-full rounded-full bg-[var(--accent)] transition-[width] duration-500 ease-out"
          style={{ width: `${usedPct}%` }}
        />
      </div>
      <p className="mt-2 text-[10px] text-[var(--textSubtle)]">Resets {resetLabel}</p>
      {credits.plan === 'free' && (
        <Link
          to="/pricing"
          className="mt-2 inline-block text-[10px] font-medium text-[var(--accent)] hover:text-[var(--accentHover)]"
        >
          Upgrade for more scans →
        </Link>
      )}
    </div>
  )
}

const SHELL_TOP_H = 'h-16'

export function AppLayoutShell() {
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const isLg = useMediaQuery('(min-width: 1024px)')
  const email = getEmailFromToken(token)
  const shell = shellMetaFromPathname(pathname)
  const visualTitle = shell?.hideTitle ? null : shell?.title ?? null
  const a11yOnly = shell?.hideTitle ? (shell.a11yTitle ?? 'Page') : null

  useEffect(() => {
    if (!token) navigate('/login', { replace: true })
  }, [token, navigate])

  if (!token) return null

  function onLogout() {
    logout()
    navigate('/login')
  }

  const navClass = ({ isActive }: { isActive: boolean }) =>
    cn(
      'flex items-center gap-3 rounded-[var(--radius-md)] px-3 py-2.5 text-sm font-medium transition-colors',
      isActive
        ? 'border-l-2 border-[var(--accent)] bg-[var(--accentSoft)] text-[var(--accent)]'
        : 'border-l-2 border-transparent text-[var(--textMuted)] hover:bg-[var(--shellNavItemHover)] hover:text-[var(--text)]',
    )

  const shellHeaderInner = (
    <>
      {visualTitle ? (
        <h1 className="font-display text-base font-semibold tracking-tight text-[var(--text)]">
          {visualTitle}
        </h1>
      ) : a11yOnly ? (
        <span className="sr-only">{a11yOnly}</span>
      ) : (
        <span className="sr-only">DealScannr</span>
      )}
    </>
  )

  return (
    <div
      className={cn(
        'flex min-h-0 flex-1 flex-col text-[var(--text)]',
        isLg ? 'max-h-[100dvh] min-h-0 overflow-hidden' : 'min-h-0 flex-1',
      )}
    >
      {isLg ? (
        <div className="grid h-full max-h-full min-h-0 min-w-0 flex-1 grid-cols-[240px_1fr] grid-rows-[4rem_minmax(0,1fr)] overflow-hidden bg-[var(--shellNav)]">
          {/* L-corner: logo + header share one row, one continuous shell surface */}
          <div className={cn('flex items-center px-4', SHELL_TOP_H)}>
            <div className="flex items-center gap-2">
              <span className="font-display text-lg font-semibold text-[var(--accent)]">DealScannr</span>
              <span className="rounded-full border border-[var(--accentBorder)] bg-[var(--accentSoft)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--accent)]">
                beta
              </span>
            </div>
          </div>
          <header
            className={cn(
              'flex items-center justify-between gap-3 px-6 lg:px-8',
              SHELL_TOP_H,
            )}
          >
            <div className="min-w-0 flex-1">{shellHeaderInner}</div>
            <ThemeToggle compact className="shrink-0" />
          </header>

          <aside
            className="flex h-full min-h-0 min-w-0 max-h-full flex-col border-0"
            aria-label="Main navigation"
          >
            <nav className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto p-3" aria-label="Main">
              {nav.map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to} className={navClass} end={to === '/dashboard'}>
                  <Icon className="h-5 w-5 shrink-0" strokeWidth={2} aria-hidden />
                  {label}
                </NavLink>
              ))}
            </nav>
            <div className="shrink-0 space-y-3 p-3">
              <CreditsBlock />
              <div className="flex items-center gap-2">
                <p className="min-w-0 flex-1 truncate text-xs text-[var(--textMuted)]" title={email ?? undefined}>
                  {email ?? 'Signed in'}
                </p>
                <button
                  type="button"
                  onClick={onLogout}
                  className="shrink-0 rounded-[var(--radius-sm)] p-2 text-[var(--textMuted)] hover:bg-[var(--shellNavItemHover)] hover:text-[var(--text)]"
                  aria-label="Log out"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            </div>
          </aside>

          <div
            className={cn(
              'min-h-0 min-w-0 overflow-y-auto border-l border-t border-[var(--contentInsetBorder)] bg-[var(--contentCanvas)]',
              'pb-24 pt-4 lg:pb-8 lg:pt-6',
              'px-4 lg:px-8',
            )}
          >
            <PageTransition>
              <Outlet />
            </PageTransition>
          </div>
        </div>
      ) : (
        <>
          <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-[var(--contentCanvas)] pb-24 pt-2">
            <div className="flex justify-end px-4">
              <ThemeToggle compact />
            </div>
            <div className="flex min-h-0 flex-1 flex-col px-4">
              <PageTransition className="min-h-0">
                <Outlet />
              </PageTransition>
            </div>
          </div>
          <nav
            className="fixed bottom-0 left-0 right-0 z-40 flex bg-[var(--shellNav)] px-2 py-2 shadow-[0_-8px_28px_-10px_rgb(0_0_0/0.12)]"
            aria-label="Mobile main"
          >
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    'flex flex-1 flex-col items-center justify-center rounded-[var(--radius-sm)] py-1',
                    isActive ? 'text-[var(--accent)]' : 'text-[var(--textMuted)]',
                  )
                }
                end={to === '/dashboard'}
              >
                <Icon className="h-6 w-6" strokeWidth={2} aria-hidden />
                <span className="sr-only">{label}</span>
              </NavLink>
            ))}
          </nav>
        </>
      )}
    </div>
  )
}

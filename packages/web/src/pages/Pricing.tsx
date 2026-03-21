import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Check } from 'lucide-react'
import { useBillingCheckoutMutation } from '@/hooks/api/billing.hooks'
import { getAxiosStatus } from '@/hooks/api/http'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { PublicLayout } from '@/components/layout/PublicLayout'
import { FaqAccordion } from '@/components/marketing/FaqAccordion'
import { cn } from '@/lib/cn'
import { useAuthStore } from '@/stores/authStore'

export function Pricing() {
  const token = useAuthStore((s) => s.token)
  const navigate = useNavigate()
  const checkoutMut = useBillingCheckoutMutation()
  const [err, setErr] = useState<string | null>(null)
  const [annual, setAnnual] = useState(false)

  useEffect(() => {
    document.title = 'Pricing — DealScannr'
  }, [])

  async function checkout(plan: 'pro' | 'team') {
    setErr(null)
    if (!token) {
      navigate('/login', { state: { from: '/pricing' } })
      return
    }
    try {
      const data = await checkoutMut.mutateAsync({ plan })
      window.location.href = data.checkout_url
    } catch (e) {
      if (getAxiosStatus(e) === 503) setErr('Billing is not configured on this server.')
      else setErr('Could not start checkout.')
    }
  }

  const proPrice = annual ? 89 : 99
  const teamPrice = annual ? 269 : 299

  return (
    <PublicLayout>
      <main className="mx-auto max-w-[960px] px-4 py-16 lg:py-24">
        <h1 className="text-center font-display text-3xl font-semibold text-[var(--text)] lg:text-4xl">
          Simple, honest pricing
        </h1>
        <p className="mx-auto mt-3 max-w-lg text-center text-lg text-[var(--textMuted)]">
          No data contracts. No per-seat minimums. Cancel anytime.
        </p>

        <div className="mt-8 flex justify-center gap-3">
          <button
            type="button"
            className={cn(
              'rounded-full px-4 py-1.5 text-sm font-medium transition-colors',
              !annual ? 'bg-[var(--accent)] text-white' : 'bg-[var(--surface2)] text-[var(--textMuted)]',
            )}
            onClick={() => setAnnual(false)}
          >
            Monthly
          </button>
          <button
            type="button"
            className={cn(
              'rounded-full px-4 py-1.5 text-sm font-medium transition-colors',
              annual ? 'bg-[var(--accent)] text-white' : 'bg-[var(--surface2)] text-[var(--textMuted)]',
            )}
            onClick={() => setAnnual(true)}
          >
            Annual <span className="text-xs opacity-90">(10% off)</span>
          </button>
        </div>

        {err && (
          <p className="mx-auto mt-6 max-w-md text-center text-sm text-[var(--red)]" role="alert">
            {err}
          </p>
        )}

        <div className="mt-12 grid gap-6 lg:grid-cols-3 lg:items-stretch">
          <Card padding="lg" className="flex flex-col">
            <h2 className="font-display text-lg font-semibold text-[var(--text)]">Free</h2>
            <p className="mt-2 text-3xl font-bold text-[var(--text)]">
              $0{' '}
              <span className="text-base font-normal text-[var(--textMuted)]">/ month</span>
            </p>
            <p className="mt-2 text-sm text-[var(--textMuted)]">For occasional due diligence</p>
            <ul className="mt-6 flex-1 space-y-2 text-sm text-[var(--text)]">
              {['3 scans per month', 'All signal lanes', 'PDF export', '7-day share links'].map((f) => (
                <li key={f} className="flex gap-2">
                  <Check className="h-4 w-4 shrink-0 text-[var(--green)]" aria-hidden />
                  {f}
                </li>
              ))}
            </ul>
            <Link to={token ? '/dashboard' : '/register'} className="mt-8 block">
              <Button variant="secondary" className="w-full">
                Get started free
              </Button>
            </Link>
          </Card>

          <Card
            padding="lg"
            className="relative flex flex-col border-2 border-[var(--accent)] shadow-dsMd"
          >
            <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-[var(--accent)] px-3 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
              Most popular
            </span>
            <h2 className="font-display text-lg font-semibold text-[var(--text)]">Pro</h2>
            <p className="mt-2 text-3xl font-bold text-[var(--text)]">
              ${proPrice}{' '}
              <span className="text-base font-normal text-[var(--textMuted)]">/ month</span>
            </p>
            <p className="mt-2 text-sm text-[var(--textMuted)]">For active angel investors</p>
            <ul className="mt-6 flex-1 space-y-2 text-sm text-[var(--text)]">
              {[
                'Everything in Free',
                '50 scans per month',
                'Watchlist (up to 50 companies)',
                'Batch scanning (up to 20 companies)',
                'API access (5 keys)',
                'Priority support',
              ].map((f) => (
                <li key={f} className="flex gap-2">
                  <Check className="h-4 w-4 shrink-0 text-[var(--green)]" aria-hidden />
                  {f}
                </li>
              ))}
            </ul>
            <Button
              type="button"
              variant="primary"
              size="lg"
              className="mt-8 w-full"
              disabled={checkoutMut.isPending}
              onClick={() => checkout('pro')}
            >
              Start with Pro
            </Button>
          </Card>

          <Card padding="lg" className="flex flex-col">
            <h2 className="font-display text-lg font-semibold text-[var(--text)]">Team</h2>
            <p className="mt-2 text-3xl font-bold text-[var(--text)]">
              ${teamPrice}{' '}
              <span className="text-base font-normal text-[var(--textMuted)]">/ month</span>
            </p>
            <p className="mt-2 text-sm text-[var(--textMuted)]">For syndicates and micro-VCs</p>
            <ul className="mt-6 flex-1 space-y-2 text-sm text-[var(--text)]">
              {[
                'Everything in Pro',
                '200 scans per month',
                'Watchlist (up to 100 companies)',
                'Batch (up to 50 companies)',
                'Shared team workspace (coming soon)',
              ].map((f) => (
                <li key={f} className="flex gap-2">
                  <Check className="h-4 w-4 shrink-0 text-[var(--green)]" aria-hidden />
                  {f}
                </li>
              ))}
            </ul>
            <Button
              type="button"
              variant="secondary"
              className="mt-8 w-full"
              disabled={checkoutMut.isPending}
              onClick={() => checkout('team')}
            >
              Start with Team
            </Button>
          </Card>
        </div>

        <div className="mt-20">
          <h2 className="text-center font-display text-xl font-semibold text-[var(--text)]">FAQ</h2>
          <div className="mx-auto mt-6 max-w-2xl">
            <FaqAccordion />
          </div>
        </div>
      </main>
    </PublicLayout>
  )
}

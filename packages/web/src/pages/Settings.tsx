import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Lock } from 'lucide-react'
import {
  useBillingCheckoutMutation,
  useBillingPortalMutation,
  useBillingStatusQuery,
} from '@/hooks/api/billing.hooks'
import {
  useApiKeysQuery,
  useCreateApiKeyMutation,
  useDeleteApiKeyMutation,
} from '@/hooks/api/apiKeys.hooks'
import { getAxiosResponseMessage, getAxiosStatus } from '@/hooks/api/http'
import { useCreditsQuery } from '@/hooks/api/users.hooks'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatusDot } from '@/components/ui/Badge'
import { useToast } from '@/components/ui/ToastContext'
import { getEmailFromToken } from '@/lib/jwt-email'
import { cn } from '@/lib/cn'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { useAuthStore } from '@/stores/authStore'

type Tab = 'account' | 'billing' | 'api'

export function Settings() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { toast } = useToast()
  const token = useAuthStore((s) => s.token)
  const email = getEmailFromToken(token)
  const enabled = Boolean(token)
  const billingQuery = useBillingStatusQuery(enabled)
  const creditsQuery = useCreditsQuery(enabled)
  const planLower = (creditsQuery.data?.plan ?? billingQuery.data?.plan ?? 'free').toLowerCase()
  const keysEligible = planLower === 'pro' || planLower === 'team'
  const keysQuery = useApiKeysQuery(enabled && keysEligible)
  const createKeyMut = useCreateApiKeyMutation()
  const deleteKeyMut = useDeleteApiKeyMutation()
  const portalMut = useBillingPortalMutation()
  const checkoutMut = useBillingCheckoutMutation()

  const [tab, setTab] = useState<Tab>('account')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [revealedKey, setRevealedKey] = useState<string | null>(null)
  const [pwCurrent, setPwCurrent] = useState('')
  const [pwNew, setPwNew] = useState('')
  const [pwConfirm, setPwConfirm] = useState('')

  useEffect(() => {
    document.title = 'Settings — DealScannr'
  }, [])

  useEffect(() => {
    if (!token) navigate('/login', { replace: true })
  }, [token, navigate])

  if (!token) return null

  const billing = billingQuery.data
  const credits = creditsQuery.data
  const loadErr =
    billingQuery.isError || creditsQuery.isError ? 'Could not load settings.' : null
  const portalErr: string | null = portalMut.isError
    ? getAxiosResponseMessage(portalMut.error) || 'Could not open billing portal.'
    : null
  const keysErr: string | null = createKeyMut.isError
    ? getAxiosResponseMessage(createKeyMut.error) || 'Could not create API key.'
    : null

  const renewal = billing?.current_period_end
    ? new Date(billing.current_period_end).toLocaleString(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
      })
    : null

  async function openPortal() {
    try {
      const data = await portalMut.mutateAsync()
      window.location.href = data.portal_url
    } catch {
      /* surfaced */
    }
  }

  async function createKey() {
    if (!newKeyName.trim()) return
    try {
      const data = await createKeyMut.mutateAsync({ name: newKeyName.trim() })
      setRevealedKey(data.key)
      setNewKeyName('')
      setShowCreateModal(false)
      toast('success', 'API key created')
    } catch {
      /* keysErr */
    }
  }

  async function checkout(plan: 'pro' | 'team') {
    try {
      const data = await checkoutMut.mutateAsync({ plan })
      window.location.href = data.checkout_url
    } catch (e) {
      if (getAxiosStatus(e) === 503) toast('error', 'Billing is not configured.')
      else toast('error', 'Could not start checkout.')
    }
  }

  const upgraded = searchParams.get('upgraded') === 'true'

  const tabs: { id: Tab; label: string }[] = [
    { id: 'account', label: 'Account' },
    { id: 'billing', label: 'Billing' },
    { id: 'api', label: 'API Keys' },
  ]

  return (
    <div className="text-[var(--text)]">
      <PageHeader title="Settings" />

      {upgraded && (
        <div className="mb-6 rounded-[var(--radius-lg)] border border-[var(--green)]/30 bg-[var(--positiveSoft)] px-4 py-3 text-sm text-[var(--green)]">
          🎉 Welcome to Pro! Your 50 monthly scans are ready.
        </div>
      )}

      <div className="mb-8 flex gap-2 border-b border-[var(--border)]">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={cn(
              'relative -mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors',
              tab === t.id
                ? 'border-[var(--accent)] text-[var(--accent)]'
                : 'border-transparent text-[var(--textMuted)] hover:text-[var(--text)]',
            )}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loadErr && <p className="mb-4 text-sm text-[var(--red)]">{loadErr}</p>}
      {portalErr && <p className="mb-4 text-sm text-[var(--red)]">{portalErr}</p>}

      {tab === 'account' && (
        <Card padding="lg" className="max-w-lg">
          <h2 className="font-display text-sm font-semibold text-[var(--text)]">Account</h2>
          <div className="mt-4">
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--textSubtle)]">Email</p>
            <p className="mt-1 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface2)] px-3 py-2 text-sm text-[var(--textMuted)]">
              {email ?? '—'}
            </p>
            <p className="mt-1 text-xs text-[var(--textSubtle)]">Email cannot be changed here.</p>
          </div>
          <div className="mt-8 flex items-center justify-between gap-4 border-t border-[var(--border)] pt-8">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--textSubtle)]">Appearance</p>
              <p className="mt-1 text-sm text-[var(--textMuted)]">Light or dark interface.</p>
            </div>
            <ThemeToggle />
          </div>
          <form
            className="mt-8 space-y-4 border-t border-[var(--border)] pt-8"
            onSubmit={(e) => {
              e.preventDefault()
              toast('warning', 'Password updates are not available in the app yet.')
            }}
          >
            <h3 className="font-display text-sm font-semibold text-[var(--text)]">Change password</h3>
            <Input
              id="pw-cur"
              label="Current password"
              type="password"
              autoComplete="current-password"
              value={pwCurrent}
              onChange={(e) => setPwCurrent(e.target.value)}
            />
            <Input
              id="pw-new"
              label="New password"
              type="password"
              autoComplete="new-password"
              value={pwNew}
              onChange={(e) => setPwNew(e.target.value)}
            />
            <Input
              id="pw-conf"
              label="Confirm new password"
              type="password"
              value={pwConfirm}
              onChange={(e) => setPwConfirm(e.target.value)}
            />
            <Button type="submit" variant="primary">
              Update password
            </Button>
          </form>
        </Card>
      )}

      {tab === 'billing' && (
        <div className="max-w-3xl space-y-6">
          <Card padding="lg">
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-full border border-[var(--accentBorder)] bg-[var(--accentSoft)] px-2.5 py-1 text-xs font-bold uppercase text-[var(--accent)]">
                {billing?.plan ?? credits?.plan ?? 'free'}
              </span>
              <span className="flex items-center gap-1.5 text-xs text-[var(--textMuted)]">
                <StatusDot status="complete" /> Active
              </span>
            </div>
            <p className="mt-3 text-sm text-[var(--textMuted)]">
              {renewal ? `Next renewal: ${renewal}` : 'Free plan — no renewal'}
            </p>
            {credits && (
              <div className="mt-6">
                <p className="text-sm text-[var(--text)]">
                  {credits.monthly_used} of {credits.monthly_limit} scans used this month
                </p>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-[var(--surface3)]">
                  <div
                    className="h-full rounded-full bg-[var(--accent)]"
                    style={{
                      width: `${credits.monthly_limit ? (credits.monthly_used / credits.monthly_limit) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>
            )}
            {billing?.stripe_customer_id && (
              <Button
                type="button"
                variant="secondary"
                className="mt-6"
                disabled={portalMut.isPending}
                onClick={openPortal}
              >
                Manage subscription →
              </Button>
            )}
          </Card>

          {planLower === 'free' && (
            <div className="grid gap-6 md:grid-cols-2">
              <Card padding="md">
                <h3 className="font-display font-semibold text-[var(--text)]">Pro</h3>
                <p className="mt-2 text-2xl font-semibold">$99/mo</p>
                <Button type="button" className="mt-4 w-full" variant="primary" onClick={() => checkout('pro')}>
                  Start with Pro
                </Button>
              </Card>
              <Card padding="md">
                <h3 className="font-display font-semibold text-[var(--text)]">Team</h3>
                <p className="mt-2 text-2xl font-semibold">$299/mo</p>
                <Button type="button" className="mt-4 w-full" variant="secondary" onClick={() => checkout('team')}>
                  Start with Team
                </Button>
              </Card>
            </div>
          )}
        </div>
      )}

      {tab === 'api' && (
        <div className="max-w-3xl">
          {!keysEligible ? (
            <Card padding="lg">
              <EmptyState
                icon={Lock}
                title="API access requires Pro or Team plan"
                description="Create programmatic access for your CRM or internal tools."
                actionLabel="Upgrade →"
                onAction={() => setTab('billing')}
              />
            </Card>
          ) : (
            <Card padding="lg">
              <div className="flex items-center justify-between gap-4">
                <h2 className="font-display text-sm font-semibold text-[var(--text)]">API keys</h2>
                <Button type="button" variant="primary" size="sm" onClick={() => setShowCreateModal(true)}>
                  Create key
                </Button>
              </div>
              {keysErr && <p className="mt-2 text-sm text-[var(--red)]">{keysErr}</p>}
              {keysQuery.isLoading && <p className="mt-4 text-sm text-[var(--textMuted)]">Loading…</p>}
              {keysQuery.data && keysQuery.data.length > 0 && (
                <div className="mt-6 overflow-x-auto rounded-[var(--radius-md)] border border-[var(--border)]">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-[var(--border)] bg-[var(--surface2)] text-xs uppercase text-[var(--textMuted)]">
                      <tr>
                        <th className="px-3 py-2">Name</th>
                        <th className="px-3 py-2">Prefix</th>
                        <th className="px-3 py-2">Created</th>
                        <th className="px-3 py-2">Last used</th>
                        <th className="px-3 py-2 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {keysQuery.data.map((k) => (
                        <tr key={k.prefix} className="border-b border-[var(--border)]/60">
                          <td className="px-3 py-2">{k.name}</td>
                          <td className="px-3 py-2 font-mono text-xs text-[var(--accent)]">{k.prefix}…</td>
                          <td className="px-3 py-2 text-[var(--textMuted)]">
                            {k.created_at ? new Date(k.created_at).toLocaleDateString() : '—'}
                          </td>
                          <td className="px-3 py-2 text-[var(--textMuted)]">
                            {k.last_used_at ? new Date(k.last_used_at).toLocaleString() : 'never'}
                          </td>
                          <td className="px-3 py-2 text-right">
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              disabled={deleteKeyMut.isPending}
                              onClick={() => void deleteKeyMut.mutateAsync(k.prefix)}
                            >
                              Delete
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          )}
        </div>
      )}

      <Modal open={showCreateModal} onClose={() => setShowCreateModal(false)} title="Create API key">
        <Input
          id="key-name"
          label="Name"
          placeholder="e.g. My CRM integration"
          value={newKeyName}
          onChange={(e) => setNewKeyName(e.target.value)}
        />
        <Button
          type="button"
          className="mt-4 w-full"
          variant="primary"
          disabled={createKeyMut.isPending || !newKeyName.trim()}
          onClick={() => void createKey()}
        >
          Create key
        </Button>
      </Modal>

      <Modal open={Boolean(revealedKey)} onClose={() => setRevealedKey(null)} title="Save your key">
        <div className="rounded-[var(--radius-md)] border border-[var(--noticeBorder)] bg-[var(--noticeBg)] px-3 py-2 text-sm text-[var(--noticeText)]">
          Copy this key now. It won&apos;t be shown again.
        </div>
        <pre className="mt-4 overflow-x-auto rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface2)] p-3 font-mono text-xs text-[var(--text)]">
          {revealedKey}
        </pre>
        <Button
          type="button"
          className="mt-4 w-full"
          variant="primary"
          onClick={async () => {
            if (!revealedKey) return
            try {
              await navigator.clipboard.writeText(revealedKey)
              toast('success', 'Key copied')
            } catch {
              toast('error', 'Copy failed')
            }
          }}
        >
          Copy key
        </Button>
        <Button type="button" className="mt-2 w-full" variant="ghost" onClick={() => setRevealedKey(null)}>
          Done
        </Button>
      </Modal>

      <div className="mt-10 flex flex-wrap gap-4 text-sm">
        <Link to="/dashboard" className="text-[var(--accent)] underline">
          Dashboard
        </Link>
        <Link to="/pricing" className="text-[var(--textMuted)] underline">
          Pricing
        </Link>
      </div>
    </div>
  )
}

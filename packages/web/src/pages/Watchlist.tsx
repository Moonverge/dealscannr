import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, Trash2 } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { ResolveEntityModal } from '@/components/entity/ResolveEntityModal'
import { getAxiosStatus } from '@/hooks/api/http'
import { useConfirmEntityMutation, useResolveEntityMutation } from '@/hooks/api/entity.hooks'
import { useCreateScanMutation } from '@/hooks/api/scans.hooks'
import type { EntityCandidate } from '@/hooks/api/types'
import {
  useAddWatchlistMutation,
  usePatchWatchlistMutation,
  useRemoveWatchlistMutation,
  useWatchlistQuery,
} from '@/hooks/api/watchlist.hooks'
import { VerdictBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { Input } from '@/components/ui/Input'
import { PageHeader } from '@/components/ui/PageHeader'
import { useToast } from '@/components/ui/ToastContext'
import { useAuthStore } from '@/stores/authStore'

const NOTIFY_OPTIONS: { value: string; label: string }[] = [
  { value: 'all', label: 'All changes' },
  { value: 'verdict_change', label: 'Verdict change' },
  { value: 'flag_detected', label: 'FLAG only' },
]

function relTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso).getTime()
  if (Number.isNaN(d)) return '—'
  const s = Math.max(0, (Date.now() - d) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} hours ago`
  if (s < 86400 * 7) return `${Math.floor(s / 86400)} days ago`
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' })
}

export function Watchlist() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const token = useAuthStore((s) => s.token)
  const enabled = Boolean(token)
  const listQuery = useWatchlistQuery(enabled)
  const resolveMut = useResolveEntityMutation()
  const confirmMut = useConfirmEntityMutation()
  const addMut = useAddWatchlistMutation()
  const patchMut = usePatchWatchlistMutation()
  const removeMut = useRemoveWatchlistMutation()
  const createScanMut = useCreateScanMutation()

  const [name, setName] = useState('')
  const [domainHint, setDomainHint] = useState('')
  const [candidates, setCandidates] = useState<EntityCandidate[]>([])
  const [confidence, setConfidence] = useState(0)
  const [showModal, setShowModal] = useState(false)
  const [manualDomain, setManualDomain] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [digestDismissed, setDigestDismissed] = useState(
    () => localStorage.getItem('dealscannr.digestBanner') === '1',
  )
  const [pendingScan, setPendingScan] = useState<{
    entityId: string
    legal: string
    domain: string
  } | null>(null)

  useEffect(() => {
    document.title = 'Watchlist — DealScannr'
  }, [])

  useEffect(() => {
    if (!token) navigate('/login', { replace: true })
  }, [token, navigate])

  const busy =
    resolveMut.isPending ||
    confirmMut.isPending ||
    addMut.isPending ||
    patchMut.isPending ||
    removeMut.isPending ||
    createScanMut.isPending

  async function resolve() {
    setErr(null)
    try {
      const data = await resolveMut.mutateAsync({
        name: name.trim(),
        domain_hint: domainHint.trim() || undefined,
      })
      setCandidates(data.candidates || [])
      setConfidence(data.confidence ?? 0)
      if (data.confidence >= 0.85 && data.candidates?.length === 1) {
        const c = data.candidates[0]
        await confirmForWatchlist(c)
      } else {
        setShowModal(true)
      }
    } catch {
      setErr('Resolve failed')
      toast('error', 'Could not resolve company')
    }
  }

  async function confirmForWatchlist(c: EntityCandidate | null, manual?: string) {
    setErr(null)
    try {
      const dom = manual ?? c?.domain ?? domainHint
      const legal = c?.legal_name ?? name.trim()
      const data = await confirmMut.mutateAsync({
        legal_name: legal,
        domain: dom,
        candidate_id: c?.candidate_id ?? undefined,
      })
      setShowModal(false)
      await addMut.mutateAsync({ entity_id: data.entity_id, notify_on: ['all'] })
      setName('')
      setDomainHint('')
      setManualDomain('')
      toast('success', 'Added to watchlist')
    } catch (e) {
      const st = getAxiosStatus(e)
      if (st === 409) setErr('Already on your watchlist')
      else setErr('Could not add to watchlist')
      toast('error', st === 409 ? 'Already on watchlist' : 'Could not add')
    }
  }

  async function runScanNow() {
    if (!pendingScan) return
    setErr(null)
    try {
      const data = await createScanMut.mutateAsync({
        entity_id: pendingScan.entityId,
        legal_name: pendingScan.legal,
        domain: pendingScan.domain,
        company_name: pendingScan.legal,
      })
      try {
        sessionStorage.setItem(
          `scan.${data.scan_id}.meta`,
          JSON.stringify({ company: pendingScan.legal, domain: pendingScan.domain }),
        )
      } catch {
        /* ignore */
      }
      await queryClient.invalidateQueries({ queryKey: ['credits'] })
      await queryClient.invalidateQueries({ queryKey: ['watchlist'] })
      setPendingScan(null)
      toast('success', 'Scan started')
      navigate(`/scan/${data.scan_id}/progress`)
    } catch (e) {
      const st = getAxiosStatus(e)
      if (st === 402) {
        setErr('No scan credits left this month.')
        toast('error', 'No credits left')
      } else if (st === 429) {
        setErr('Too many scans — wait and try again.')
        toast('warning', 'Rate limited')
      } else {
        setErr('Scan failed')
        toast('error', 'Scan failed')
      }
    }
  }

  if (!token) return null

  const entries = listQuery.data ?? []

  return (
    <div className="text-[var(--text)]">
      <PageHeader
        title="Watchlist"
        subtitle="Track companies for weekly digest emails and on-demand rescans."
        actions={
          <Button
            type="button"
            variant="primary"
            size="md"
            onClick={() => document.getElementById('watchlist-add')?.scrollIntoView({ behavior: 'smooth' })}
          >
            Add company
          </Button>
        }
      />

      {!digestDismissed && (
        <div className="mb-6 flex items-start gap-3 rounded-[var(--radius-lg)] border border-[var(--noticeBorder)] bg-[var(--noticeBg)] px-4 py-3 text-sm text-[var(--noticeText)]">
          <span aria-hidden>📬</span>
          <p className="flex-1">
            You&apos;ll receive a weekly digest every Monday with updates on all watched companies.
          </p>
          <button
            type="button"
            className="shrink-0 rounded p-1 text-[var(--noticeText)] hover:bg-black/5"
            aria-label="Dismiss"
            onClick={() => {
              setDigestDismissed(true)
              localStorage.setItem('dealscannr.digestBanner', '1')
            }}
          >
            ×
          </button>
        </div>
      )}

      <Card id="watchlist-add" padding="md" className="max-w-lg">
        <h2 className="font-display text-sm font-semibold text-[var(--text)]">Add company</h2>
        <div className="mt-4 space-y-3">
          <Input
            id="wl-name"
            label="Legal name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Input
            id="wl-domain"
            label="Domain hint (optional)"
            value={domainHint}
            onChange={(e) => setDomainHint(e.target.value)}
            helperText="Helps disambiguate common names."
          />
          <Button type="button" variant="primary" disabled={busy || !name.trim()} onClick={() => void resolve()}>
            Resolve & add
          </Button>
        </div>
      </Card>

      {err && (
        <p className="mt-4 text-sm text-[var(--red)]" role="alert">
          {err}
        </p>
      )}

      {listQuery.isLoading && <p className="mt-8 text-sm text-[var(--textMuted)]">Loading…</p>}

      {!listQuery.isLoading && entries.length === 0 && (
        <Card padding="lg" className="mt-8">
          <EmptyState
            icon={Eye}
            title="No companies on your watchlist"
            description="Add companies you are tracking to receive weekly digest emails."
            actionLabel="Add your first company"
            onAction={() => document.getElementById('watchlist-add')?.scrollIntoView({ behavior: 'smooth' })}
          />
        </Card>
      )}

      {entries.length > 0 && (
        <div className="mt-8 space-y-3">
          <div className="hidden grid-cols-[1fr_auto_auto_auto] gap-4 border-b border-[var(--border)] pb-2 text-xs font-semibold uppercase tracking-wide text-[var(--textSubtle)] lg:grid">
            <span>Company</span>
            <span>Last verdict</span>
            <span>Last scanned</span>
            <span className="text-right">Actions</span>
          </div>
          {entries.map((row) => {
            const notifyVal = (row.notify_on?.[0] as string) || 'all'
            return (
              <Card key={row.id} hover padding="md">
                <div className="flex flex-col gap-4 lg:grid lg:grid-cols-[1fr_auto_auto_auto] lg:items-center lg:gap-4">
                  <div>
                    <p className="font-medium text-[var(--text)]">{row.entity_name || '—'}</p>
                    <p className="font-mono text-xs text-[var(--textMuted)]">{row.domain || '—'}</p>
                  </div>
                  <div>
                    {row.last_verdict ? (
                      <VerdictBadge verdict={row.last_verdict} size="sm" />
                    ) : (
                      <span className="text-xs text-[var(--textSubtle)]">—</span>
                    )}
                  </div>
                  <div>
                    <p className="text-sm text-[var(--text)]" title={row.last_scanned_at ?? undefined}>
                      {relTime(row.last_scanned_at)}
                    </p>
                    <p className="text-[10px] text-[var(--textSubtle)] lg:hidden">Last scanned</p>
                  </div>
                  <div className="flex flex-col gap-3 lg:items-end">
                    <label className="flex items-center gap-2 text-xs text-[var(--textMuted)]">
                      <span className="hidden lg:inline">Notify</span>
                      <select
                        className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-2 py-1.5 text-sm text-[var(--text)]"
                        value={notifyVal}
                        onChange={(e) => {
                          const v = e.target.value
                          void patchMut.mutateAsync({ entityId: row.entity_id, notify_on: [v] })
                        }}
                        disabled={patchMut.isPending}
                      >
                        {NOTIFY_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {pendingScan?.entityId === row.entity_id ? (
                        <div className="w-full rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface2)] p-3 text-sm text-[var(--text)]">
                          <p>This will use 1 scan credit. Continue?</p>
                          <div className="mt-2 flex gap-2">
                            <Button type="button" size="sm" variant="primary" disabled={busy} onClick={runScanNow}>
                              Continue
                            </Button>
                            <Button type="button" size="sm" variant="ghost" onClick={() => setPendingScan(null)}>
                              Cancel
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            disabled={busy}
                            onClick={() =>
                              setPendingScan({
                                entityId: row.entity_id,
                                legal: row.entity_name || row.entity_id,
                                domain: row.domain || '',
                              })
                            }
                          >
                            Scan now
                          </Button>
                          <button
                            type="button"
                            className="rounded p-2 text-[var(--red)] hover:bg-[var(--negativeSoft)]"
                            aria-label={`Remove ${row.entity_name}`}
                            disabled={busy}
                            onClick={() => void removeMut.mutateAsync(row.entity_id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      )}

      <ResolveEntityModal
        open={showModal}
        onClose={() => setShowModal(false)}
        candidates={candidates}
        confidence={confidence}
        busy={busy}
        manualDomain={manualDomain}
        onManualDomainChange={setManualDomain}
        onPickCandidate={(c) => void confirmForWatchlist(c)}
        onConfirmManual={() => void confirmForWatchlist(null, manualDomain.trim())}
      />
    </div>
  )
}

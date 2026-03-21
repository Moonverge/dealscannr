import { useCallback, useEffect, useState, type DragEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Upload, FileDown } from 'lucide-react'
import { getAxiosStatus } from '@/hooks/api/http'
import { useBatchStatusQuery, useBatchUploadMutation } from '@/hooks/api/batch.hooks'
import { useCreditsQuery } from '@/hooks/api/users.hooks'
import { VerdictBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { PageHeader } from '@/components/ui/PageHeader'
import { Spinner } from '@/components/ui/Spinner'
import { useToast } from '@/components/ui/ToastContext'
import { useAuthStore } from '@/stores/authStore'

const TEMPLATE = 'company_name,domain\nStripe,stripe.com\n'

function parseBatchCsv(text: string): { company_name: string; domain: string }[] {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
  if (lines.length < 2) return []
  const header = lines[0].split(',').map((s) => s.trim().toLowerCase())
  const ni = header.indexOf('company_name')
  const di = header.indexOf('domain')
  if (ni < 0) return []
  const out: { company_name: string; domain: string }[] = []
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(',').map((s) => s.trim().replace(/^"|"$/g, ''))
    const cn = cols[ni]?.trim()
    if (!cn) continue
    out.push({ company_name: cn, domain: di >= 0 ? (cols[di] ?? '').trim() : '' })
  }
  return out
}

export function Batch() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const token = useAuthStore((s) => s.token)
  const enabled = Boolean(token)
  const creditsQuery = useCreditsQuery(enabled)
  const uploadMut = useBatchUploadMutation()
  const [batchId, setBatchId] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [stagedFile, setStagedFile] = useState<File | null>(null)
  const [parsedRows, setParsedRows] = useState<{ company_name: string; domain: string }[]>([])

  const tier = (creditsQuery.data?.plan ?? 'free').toLowerCase()
  const eligible = tier === 'pro' || tier === 'team'
  const credits = creditsQuery.data

  const statusQuery = useBatchStatusQuery(batchId, Boolean(batchId))

  useEffect(() => {
    document.title = 'Batch scan — DealScannr'
  }, [])

  useEffect(() => {
    if (!token) navigate('/login', { replace: true })
  }, [token, navigate])

  const processFileStaging = useCallback(async (file: File) => {
    setErr(null)
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setErr('Please upload a .csv file')
      return
    }
    try {
      const text = await file.text()
      const rows = parseBatchCsv(text)
      if (rows.length === 0) {
        setErr('No rows found — include a company_name column.')
        return
      }
      setStagedFile(file)
      setParsedRows(rows)
      setBatchId(null)
    } catch {
      setErr('Could not read file')
    }
  }, [])

  async function startBatch() {
    if (!stagedFile) return
    setErr(null)
    try {
      const data = await uploadMut.mutateAsync(stagedFile)
      setBatchId(data.batch_id)
      setStagedFile(null)
      setParsedRows([])
      toast('success', 'Batch scan started')
    } catch (e) {
      const st = getAxiosStatus(e)
      if (st === 403) setErr('Batch scan requires Pro or Team.')
      else if (st === 402) setErr('Not enough credits for this batch.')
      else if (st === 400) setErr('Invalid CSV — include a company_name column.')
      else setErr('Upload failed')
      toast('error', 'Batch failed to start')
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files?.[0]
    if (f) void processFileStaging(f)
  }

  function downloadTemplate() {
    const blob = new Blob([TEMPLATE], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'dealscannr-batch-template.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  function downloadResultsCsv() {
    const rows = statusQuery.data?.results ?? []
    const header = 'company_name,domain,scan_id,verdict,status,error\n'
    const body = rows
      .map((r) =>
        [
          r.company_name ?? '',
          r.domain ?? '',
          r.scan_id ?? '',
          r.verdict ?? '',
          r.status ?? '',
          (r.error ?? '').replace(/"/g, '""'),
        ]
          .map((c) => `"${c}"`)
          .join(','),
      )
      .join('\n')
    const blob = new Blob([header + body], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'dealscannr-batch-results.csv'
    a.click()
    URL.revokeObjectURL(url)
    toast('info', 'Results CSV downloaded')
  }

  if (!token) return null

  const preview = parsedRows.slice(0, 5)
  const more = Math.max(0, parsedRows.length - preview.length)
  const cost = parsedRows.length
  const remaining = credits?.remaining ?? 0
  const complete = statusQuery.data?.status === 'complete'

  return (
    <div className="text-[var(--text)]">
      <PageHeader title="Batch scan" subtitle="Upload a CSV to scan many companies in one run." />

      {!eligible && (
        <Card padding="md" className="mb-6 max-w-2xl border-[var(--noticeBorder)] bg-[var(--noticeBg)]">
          <p className="text-sm font-medium text-[var(--noticeText)]">Batch scanning requires Pro or Team plan</p>
          <Link to="/pricing" className="mt-3 inline-block">
            <Button variant="primary" size="sm">
              Upgrade →
            </Button>
          </Link>
        </Card>
      )}

      {eligible && !batchId && (
        <>
          <button
            type="button"
            onClick={downloadTemplate}
            className="mb-4 inline-flex items-center gap-2 text-sm font-medium text-[var(--accent)] hover:text-[var(--accentHover)]"
          >
            <FileDown className="h-4 w-4" aria-hidden /> Download CSV template
          </button>
          <div
            onDragOver={(e) => {
              e.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            className={`mb-6 flex min-h-[200px] cursor-pointer flex-col items-center justify-center rounded-[var(--radius-xl)] border-2 border-dashed px-6 py-10 transition-colors ${
              dragOver
                ? 'border-[var(--accent)] bg-[var(--accentSoft)]'
                : 'border-[var(--border)] bg-[var(--surface)]'
            }`}
          >
            <Upload className="h-10 w-10 text-[var(--textMuted)]" strokeWidth={1.25} aria-hidden />
            <p className="mt-3 text-sm text-[var(--textMuted)]">Drag your CSV here or click to browse</p>
            <p className="mt-1 font-mono text-xs text-[var(--textSubtle)]">company_name, domain (optional)</p>
            <label className="mt-4">
              <input
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) void processFileStaging(f)
                  e.target.value = ''
                }}
              />
              <span className="cursor-pointer rounded-[var(--radius-md)] bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accentHover)]">
                Browse files
              </span>
            </label>
          </div>
        </>
      )}

      {err && (
        <p className="mb-4 text-sm text-[var(--red)]" role="alert">
          {err}
        </p>
      )}

      {eligible && stagedFile && parsedRows.length > 0 && !batchId && (
        <Card padding="md" className="mb-8 max-w-3xl">
          <p className="text-sm font-medium text-[var(--text)]">
            {parsedRows.length} companies · Preview
          </p>
          <div className="mt-4 overflow-x-auto rounded-[var(--radius-md)] border border-[var(--border)]">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-[var(--border)] bg-[var(--surface2)] text-xs uppercase text-[var(--textMuted)]">
                <tr>
                  <th className="px-3 py-2">#</th>
                  <th className="px-3 py-2">Company name</th>
                  <th className="px-3 py-2">Domain</th>
                  <th className="px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {preview.map((r, i) => (
                  <tr key={i} className="border-b border-[var(--border)]/60">
                    <td className="px-3 py-2 text-[var(--textMuted)]">{i + 1}</td>
                    <td className="px-3 py-2 text-[var(--text)]">{r.company_name}</td>
                    <td className="px-3 py-2 font-mono text-xs text-[var(--textMuted)]">{r.domain || '—'}</td>
                    <td className="px-3 py-2 text-[var(--textSubtle)]">Ready</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {more > 0 && <p className="mt-2 text-xs text-[var(--textMuted)]">+ {more} more</p>}
          <p className="mt-4 text-sm text-[var(--textMuted)]">
            This will use <span className="font-medium text-[var(--text)]">{cost}</span> scan credits. You
            have <span className="font-medium text-[var(--text)]">{remaining}</span> remaining.
          </p>
          <Button
            type="button"
            className="mt-4"
            variant="primary"
            onClick={startBatch}
            loading={uploadMut.isPending}
          >
            Start batch scan
          </Button>
        </Card>
      )}

      {batchId && statusQuery.data && (
        <Card padding="md" className="max-w-4xl">
          {complete && (
            <div className="mb-4 rounded-[var(--radius-md)] border border-[var(--green)]/30 bg-[var(--positiveSoft)] px-3 py-2 text-sm text-[var(--green)]">
              All {statusQuery.data.total} scans complete
            </div>
          )}
          {!complete && (
            <p className="mb-4 text-sm text-[var(--textMuted)]">
              {statusQuery.data.completed} of {statusQuery.data.total} complete — we&apos;ll email you when
              finished.
            </p>
          )}
          <div className="mb-4 h-2 overflow-hidden rounded-full bg-[var(--surface3)]">
            <div
              className="h-full rounded-full bg-[var(--accent)] transition-all duration-500"
              style={{
                width: `${statusQuery.data.total ? (statusQuery.data.completed / statusQuery.data.total) * 100 : 0}%`,
              }}
            />
          </div>
          <div className="overflow-x-auto rounded-[var(--radius-md)] border border-[var(--border)]">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-[var(--border)] bg-[var(--surface2)] text-xs uppercase text-[var(--textMuted)]">
                <tr>
                  <th className="px-3 py-2">Company</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Verdict</th>
                  <th className="px-3 py-2">Report</th>
                </tr>
              </thead>
              <tbody>
                {statusQuery.data.results.map((r, i) => (
                  <tr key={i} className="border-b border-[var(--border)]/60">
                    <td className="px-3 py-2 text-[var(--text)]">{r.company_name ?? '—'}</td>
                    <td className="px-3 py-2 text-[var(--textMuted)]">
                      {r.status === 'running' && (
                        <span className="inline-flex items-center gap-2">
                          <Spinner size="sm" /> Running
                        </span>
                      )}
                      {r.status === 'complete' && 'Done'}
                      {r.status === 'pending' && 'Queued'}
                      {r.status === 'failed' && (r.error || 'Failed')}
                      {!['complete', 'pending', 'failed', 'running'].includes(r.status || '') &&
                        (r.status ?? '—')}
                    </td>
                    <td className="px-3 py-2">
                      {r.verdict ? <VerdictBadge verdict={r.verdict} size="sm" /> : '—'}
                    </td>
                    <td className="px-3 py-2">
                      {r.scan_id && r.status === 'complete' ? (
                        <Link
                          to={`/scan/${r.scan_id}/report`}
                          className="text-[var(--accent)] underline hover:text-[var(--accentHover)]"
                        >
                          View
                        </Link>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {complete && (
            <Button type="button" variant="secondary" className="mt-4" onClick={downloadResultsCsv}>
              Download results CSV
            </Button>
          )}
        </Card>
      )}
    </div>
  )
}

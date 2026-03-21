import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useRegisterMutation } from '@/hooks/api/auth.hooks'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { PublicLayout } from '@/components/layout/PublicLayout'
import { useAuthStore } from '@/stores/authStore'

function strength(pw: string): 'weak' | 'fair' | 'strong' {
  if (pw.length < 8) return 'weak'
  const hasMix = /[a-z]/.test(pw) && /[A-Z]/.test(pw) && /\d/.test(pw)
  if (pw.length >= 12 && hasMix) return 'strong'
  if (pw.length >= 10 || hasMix) return 'fair'
  return 'weak'
}

export function Register() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const setToken = useAuthStore((s) => s.setToken)
  const registerMut = useRegisterMutation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [fieldErr, setFieldErr] = useState<{ email?: string; password?: string; confirm?: string }>({})

  const intent = searchParams.get('intent')
  const company = searchParams.get('company')

  useEffect(() => {
    document.title = 'Create account — DealScannr'
  }, [])

  const str = useMemo(() => strength(password), [password])
  const strColor =
    str === 'weak' ? 'bg-[var(--red)]' : str === 'fair' ? 'bg-[var(--yellow)]' : 'bg-[var(--green)]'
  const strPct = str === 'weak' ? 33 : str === 'fair' ? 66 : 100

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setErr(null)
    setFieldErr({})
    const fe: typeof fieldErr = {}
    if (!email.trim()) fe.email = 'Enter your email'
    if (password.length < 8) fe.password = 'At least 8 characters'
    if (password !== confirm) fe.confirm = 'Passwords do not match'
    if (Object.keys(fe).length) {
      setFieldErr(fe)
      return
    }
    try {
      const data = await registerMut.mutateAsync({ email: email.trim(), password })
      setToken(data.token)
      if (intent === 'scan' && company?.trim()) {
        navigate(
          `/dashboard?intent=scan&company=${encodeURIComponent(company.trim())}`,
          { replace: true },
        )
      } else {
        navigate('/dashboard', { replace: true })
      }
    } catch {
      setErr('Could not create account. Email may already be registered.')
    }
  }

  return (
    <PublicLayout>
      <main className="flex min-h-[calc(100vh-200px)] items-center justify-center px-4 py-12">
        <Card
          padding="lg"
          className="w-full max-w-[400px] opacity-0 animate-[ds-login-in_300ms_ease-out_forwards]"
        >
          <style>{`
            @keyframes ds-login-in {
              from { opacity: 0; transform: translateY(8px); }
              to { opacity: 1; transform: translateY(0); }
            }
          `}</style>
          <div className="mb-6 text-center">
            <div className="mx-auto mb-4 flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] bg-[var(--accentSoft)] font-display text-lg font-bold text-[var(--accent)]">
              D
            </div>
            <h1 className="font-display text-xl font-semibold text-[var(--text)]">Create your account</h1>
            <p className="mt-1 text-sm text-[var(--textMuted)]">Start scanning in minutes</p>
          </div>

          {intent === 'scan' && company?.trim() && (
            <div
              className="mb-4 rounded-[var(--radius-md)] border border-[var(--noticeBorder)] bg-[var(--noticeBg)] px-3 py-2 text-sm text-[var(--noticeText)]"
              role="status"
            >
              After signup you can scan <span className="font-medium">{company.trim()}</span> from your
              dashboard.
            </div>
          )}

          <form className="space-y-4" onSubmit={onSubmit} noValidate>
            <Input
              id="reg-email"
              label="Email address"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={fieldErr.email}
            />
            <div>
              <Input
                id="reg-password"
                label="Password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                error={fieldErr.password}
              />
              <div className="mt-2 h-1 overflow-hidden rounded-full bg-[var(--surface3)]">
                <div
                  className={`h-full transition-all duration-300 ${strColor}`}
                  style={{ width: `${strPct}%` }}
                />
              </div>
              <p className="mt-1 text-xs capitalize text-[var(--textMuted)]">{str} password</p>
            </div>
            <Input
              id="reg-confirm"
              label="Confirm password"
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              error={fieldErr.confirm}
            />
            {err && (
              <p className="text-sm text-[var(--red)]" role="alert">
                {err}
              </p>
            )}
            <Button type="submit" variant="primary" className="w-full" size="lg" loading={registerMut.isPending}>
              Create account
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-[var(--textSubtle)]">
            By creating an account you agree to our Terms of Service.
          </p>

          <p className="mt-4 text-center text-sm text-[var(--textMuted)]">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-[var(--accent)] hover:text-[var(--accentHover)]">
              Sign in →
            </Link>
          </p>
        </Card>
      </main>
    </PublicLayout>
  )
}

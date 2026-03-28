import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import type { GuestTrialModalVariant } from '@/lib/guest-trial-errors'

const COPY: Record<
  GuestTrialModalVariant,
  { title: string; body: string }
> = {
  session: {
    title: 'Trial session unavailable',
    body:
      'We could not verify your trial browser session (cookies may be blocked or the session expired). Create a free account to keep scans, or enable cookies and start again from Try scan.',
  },
  exhausted: {
    title: 'Trial scan already used',
    body:
      'Your free trial scan on this browser has already been used. Sign up to run more due diligence scans and keep everything in your dashboard.',
  },
  ip_limit: {
    title: 'Trial limit on this network',
    body:
      'A trial scan was already used from this network recently. Create a free account to continue scanning.',
  },
}

export function GuestTrialGateModal({
  open,
  onClose,
  variant,
}: {
  open: boolean
  onClose: () => void
  variant: GuestTrialModalVariant | null
}) {
  if (!variant) return null
  const { title, body } = COPY[variant]

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-sm leading-relaxed text-[var(--textMuted)]">{body}</p>
      <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-end">
        <Link to="/register" className="sm:order-2">
          <Button type="button" variant="primary" size="md" className="w-full sm:w-auto">
            Create free account
          </Button>
        </Link>
        <Link to="/login" className="sm:order-1">
          <Button type="button" variant="ghost" size="md" className="w-full sm:w-auto">
            Sign in
          </Button>
        </Link>
      </div>
    </Modal>
  )
}

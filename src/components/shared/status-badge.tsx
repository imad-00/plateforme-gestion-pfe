import { cn } from '@/lib/utils'

// ─── Tier mapping ─────────────────────────────────────────────────────────────
// Every backend status string maps to one of four visual tiers defined in the
// Style Guide. Unknown values fall back to neutral.

type StatusTier = 'success' | 'warning' | 'error' | 'neutral'

const TIER: Record<string, StatusTier> = {
  // success
  APPROVED:    'success',
  ACCEPTED:    'success',
  ACTIVE:      'success',
  VALIDATED:   'success',
  // warning
  SUBMITTED:   'warning',
  PENDING:     'warning',
  LOCKED:      'warning',
  FORMING:     'warning',
  // error
  REJECTED:    'error',
  DISSOLVED:   'error',
  SUSPENDED:   'error',
  ARCHIVED:    'error',
  NEEDS_REVISION: 'error',
  // neutral
  DRAFT:       'neutral',
  CLOSED:      'neutral',
  ENDED:       'neutral',
}

const TIER_CLASSES: Record<StatusTier, string> = {
  success: 'bg-status-success-bg text-status-success-fg border-status-success-border',
  warning: 'bg-status-warning-bg text-status-warning-fg border-status-warning-border',
  error:   'bg-status-error-bg   text-status-error-fg   border-status-error-border',
  neutral: 'bg-status-neutral-bg text-status-neutral-fg border-status-neutral-border',
}

// "NEEDS_REVISION" → "Needs Revision"
function toLabel(status: string): string {
  return status
    .split('_')
    .map(w => w.charAt(0) + w.slice(1).toLowerCase())
    .join(' ')
}

// ─── Component ────────────────────────────────────────────────────────────────

interface StatusBadgeProps {
  status: string
  label?: string    // override the auto-formatted label
  className?: string
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const tier = TIER[status.toUpperCase()] ?? 'neutral'
  return (
    <span
      className={cn(
        'inline-flex h-5 items-center rounded-full border px-2.5 text-xs font-medium whitespace-nowrap',
        TIER_CLASSES[tier],
        className,
      )}
    >
      {label ?? toLabel(status)}
    </span>
  )
}

'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { CheckCircle2, Eye, EyeOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { cn } from '@/lib/utils'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

type Step = 'request' | 'verify' | 'confirm' | 'done'

// ─── Step progress dots ───────────────────────────────────────────────────────

function StepDots({ current }: { current: 1 | 2 | 3 }) {
  return (
    <div className="flex items-center gap-1" aria-hidden="true">
      {([1, 2, 3] as const).map(n => (
        <div
          key={n}
          className={cn(
            'h-1.5 rounded-full transition-all duration-300',
            n < current
              ? 'w-4 bg-primary/50'
              : n === current
                ? 'w-6 bg-primary'
                : 'w-2 bg-border',
          )}
        />
      ))}
    </div>
  )
}

// ─── Inline error alert ───────────────────────────────────────────────────────

function ErrorAlert({ message }: { message: string }) {
  return (
    <p
      role="alert"
      className="rounded-lg border border-status-error-border bg-status-error-bg px-3 py-2 text-sm text-status-error-fg"
    >
      {message}
    </p>
  )
}

// ─── Password field with visibility toggle ────────────────────────────────────

function PasswordInput({
  id,
  label,
  show,
  onToggle,
  disabled,
  invalid,
  errorMessage,
  ...inputProps
}: {
  id: string
  label: string
  show: boolean
  onToggle: () => void
  disabled?: boolean
  invalid?: boolean
  errorMessage?: string
} & Omit<React.ComponentProps<'input'>, 'type' | 'id'>) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input
          id={id}
          type={show ? 'text' : 'password'}
          autoComplete="new-password"
          placeholder="••••••••"
          className="pr-9"
          disabled={disabled}
          aria-invalid={invalid}
          {...inputProps}
        />
        <button
          type="button"
          onClick={onToggle}
          tabIndex={-1}
          aria-label={show ? 'Hide password' : 'Show password'}
          className="absolute inset-y-0 right-0 flex items-center px-2.5 text-muted-foreground transition-colors hover:text-foreground"
        >
          {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
        </button>
      </div>
      {errorMessage && (
        <p className="text-xs text-status-error-fg">{errorMessage}</p>
      )}
    </div>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function ForgotPasswordView() {
  const router = useRouter()

  const [step, setStep] = useState<Step>('request')
  const [identifier, setIdentifier] = useState('')
  const [otpDebug, setOtpDebug] = useState<string | null>(null)
  const [verificationToken, setVerificationToken] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [resendCooldown, setResendCooldown] = useState(0)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  useEffect(() => {
    if (resendCooldown <= 0) return
    const timer = setTimeout(() => setResendCooldown(c => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [resendCooldown])

  // Instantiate all three forms unconditionally (rules of hooks)
  const {
    register: regRequest,
    handleSubmit: handleRequest,
    formState: { isSubmitting: requestPending },
  } = useForm<{ identifier: string }>()

  const {
    register: regVerify,
    handleSubmit: handleVerify,
    formState: { isSubmitting: verifyPending },
  } = useForm<{ otp: string }>()

  const {
    register: regConfirm,
    handleSubmit: handleConfirm,
    formState: { errors: confirmErrors, isSubmitting: confirmPending },
    getValues: getConfirmValues,
  } = useForm<{ new_password: string; confirm_password: string }>()

  // ── Helpers ────────────────────────────────────────────────────────────────

  function extractErrorMessage(data: Record<string, unknown>): string {
    if (typeof data.detail === 'string') return data.detail
    const first = Object.values(data)
      .flatMap(v => (Array.isArray(v) ? v : [v]))
      .find(v => typeof v === 'string')
    return typeof first === 'string' ? first : 'An unexpected error occurred.'
  }

  // ── Step 1: Request OTP ────────────────────────────────────────────────────

  async function onRequestOtp({ identifier: id }: { identifier: string }) {
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/auth/password-reset/request-otp/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: id }),
      })
      const data = (await res.json()) as Record<string, unknown>
      if (!res.ok) throw new Error(extractErrorMessage(data))

      setIdentifier(id)
      if (typeof data.otp_debug === 'string') setOtpDebug(data.otp_debug)
      setStep('verify')
      setResendCooldown(60)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.')
    }
  }

  // ── Step 2: Verify OTP ─────────────────────────────────────────────────────

  async function onVerifyOtp({ otp }: { otp: string }) {
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/auth/password-reset/verify-otp/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier, otp }),
      })
      const data = (await res.json()) as Record<string, unknown>
      if (!res.ok) throw new Error(extractErrorMessage(data))
      if (typeof data.verification_token !== 'string')
        throw new Error('Invalid response from server.')

      setVerificationToken(data.verification_token)
      setStep('confirm')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.')
    }
  }

  async function onResend() {
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/auth/password-reset/resend-otp/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier }),
      })
      if (!res.ok) {
        const data = (await res.json()) as Record<string, unknown>
        throw new Error(extractErrorMessage(data))
      }
      setResendCooldown(60)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.')
    }
  }

  // ── Step 3: Confirm new password ───────────────────────────────────────────

  async function onConfirmPassword({
    new_password,
    confirm_password,
  }: {
    new_password: string
    confirm_password: string
  }) {
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/auth/password-reset/confirm/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          identifier,
          verification_token: verificationToken,
          new_password,
          confirm_password,
        }),
      })
      if (!res.ok) {
        const data = (await res.json()) as Record<string, unknown>
        throw new Error(extractErrorMessage(data))
      }
      setStep('done')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.')
    }
  }

  const stepNumber = (step === 'request' ? 1 : step === 'verify' ? 2 : 3) as 1 | 2 | 3

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="flex w-full max-w-sm flex-col gap-4">
      {step === 'done' ? (
        <Card className="shadow-card">
          <CardContent className="flex flex-col items-center gap-4 py-8 text-center">
            <div className="flex size-12 items-center justify-center rounded-full bg-status-success-bg text-status-success-fg">
              <CheckCircle2 className="size-6" />
            </div>
            <div className="space-y-1">
              <p className="font-semibold text-foreground">Password updated</p>
              <p className="text-sm text-muted-foreground">
                You can now sign in with your new password.
              </p>
            </div>
            <Button size="lg" className="w-full" onClick={() => router.push('/login')}>
              Go to sign in
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>
              {step === 'request' && 'Reset your password'}
              {step === 'verify' && 'Check your email'}
              {step === 'confirm' && 'Set a new password'}
            </CardTitle>
            <CardDescription>
              {step === 'request' &&
                "Enter your matricule or email and we'll send you a reset code."}
              {step === 'verify' && `We sent a 6-digit code to ${identifier}.`}
              {step === 'confirm' && 'Choose a strong password for your account.'}
            </CardDescription>
            <CardAction>
              <StepDots current={stepNumber} />
            </CardAction>
          </CardHeader>

          <CardContent className="flex flex-col gap-4">
            {/* ── Step 1 ── */}
            {step === 'request' && (
              <form
                onSubmit={handleRequest(onRequestOtp)}
                className="flex flex-col gap-4"
              >
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="reset-identifier">Matricule or email</Label>
                  <Input
                    id="reset-identifier"
                    autoComplete="username"
                    placeholder="191234 or you@univ.dz"
                    disabled={requestPending}
                    {...regRequest('identifier', { required: true })}
                  />
                </div>
                {error && <ErrorAlert message={error} />}
                <Button
                  type="submit"
                  size="lg"
                  className="w-full"
                  disabled={requestPending}
                >
                  {requestPending ? 'Sending…' : 'Send reset code'}
                </Button>
              </form>
            )}

            {/* ── Step 2 ── */}
            {step === 'verify' && (
              <form
                onSubmit={handleVerify(onVerifyOtp)}
                className="flex flex-col gap-4"
              >
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="otp">6-digit code</Label>
                  <Input
                    id="otp"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    placeholder="123456"
                    disabled={verifyPending}
                    {...regVerify('otp', {
                      required: true,
                      minLength: 6,
                      maxLength: 6,
                    })}
                  />
                </div>

                {otpDebug && (
                  <p className="rounded-lg border border-status-warning-border bg-status-warning-bg px-3 py-2 text-xs text-status-warning-fg">
                    <span className="font-medium">Dev hint — </span>
                    OTP is{' '}
                    <span className="font-mono font-semibold">{otpDebug}</span>
                  </p>
                )}

                {error && <ErrorAlert message={error} />}

                <Button
                  type="submit"
                  size="lg"
                  className="w-full"
                  disabled={verifyPending}
                >
                  {verifyPending ? 'Verifying…' : 'Verify code'}
                </Button>

                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Didn't receive it?</span>
                  <button
                    type="button"
                    onClick={onResend}
                    disabled={resendCooldown > 0}
                    className="text-primary underline-offset-4 hover:underline disabled:pointer-events-none disabled:text-muted-foreground"
                  >
                    {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Resend code'}
                  </button>
                </div>
              </form>
            )}

            {/* ── Step 3 ── */}
            {step === 'confirm' && (
              <form
                onSubmit={handleConfirm(onConfirmPassword)}
                className="flex flex-col gap-4"
              >
                <PasswordInput
                  id="new-password"
                  label="New password"
                  show={showNewPassword}
                  onToggle={() => setShowNewPassword(v => !v)}
                  disabled={confirmPending}
                  invalid={!!confirmErrors.new_password}
                  errorMessage={confirmErrors.new_password?.message}
                  {...regConfirm('new_password', {
                    required: true,
                    minLength: {
                      value: 8,
                      message: 'Must be at least 8 characters.',
                    },
                  })}
                />

                <PasswordInput
                  id="confirm-password"
                  label="Confirm new password"
                  show={showConfirmPassword}
                  onToggle={() => setShowConfirmPassword(v => !v)}
                  disabled={confirmPending}
                  invalid={!!confirmErrors.confirm_password}
                  errorMessage={confirmErrors.confirm_password?.message}
                  {...regConfirm('confirm_password', {
                    required: true,
                    validate: v =>
                      v === getConfirmValues('new_password') ||
                      'Passwords do not match.',
                  })}
                />

                {error && <ErrorAlert message={error} />}

                <Button
                  type="submit"
                  size="lg"
                  className="w-full"
                  disabled={confirmPending}
                >
                  {confirmPending ? 'Resetting…' : 'Reset password'}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      )}

      <p className="text-center text-sm text-muted-foreground">
        <Link
          href="/login"
          className="text-primary underline-offset-4 hover:underline"
        >
          Back to sign in
        </Link>
      </p>
    </div>
  )
}

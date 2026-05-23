'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { Eye, EyeOff } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import type { User } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface LoginFormValues {
  identifier: string
  password: string
}

function defaultRoute(user: User): string {
  if (user.platform_access_level) return '/admin/users'
  switch (user.business_identity) {
    case 'STUDENT': return '/student/team'
    case 'TEACHER': return '/teacher/subjects'
    case 'EXTERNAL_SUPERVISOR': return '/teacher/supervision'
    default: return '/admin/users'
  }
}

export function LoginView() {
  const { login } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const [showPassword, setShowPassword] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<LoginFormValues>()

  async function onSubmit(values: LoginFormValues) {
    setServerError(null)
    try {
      const user = await login(values.identifier, values.password)
      const next = searchParams.get('next')
      router.push(next && next.startsWith('/') ? next : defaultRoute(user))
    } catch (err) {
      setServerError(err instanceof Error ? err.message : 'An unexpected error occurred.')
    }
  }

  return (
    <div className="flex w-full max-w-sm flex-col gap-4">
      <Card className="shadow-card">
        <CardHeader>
          <CardTitle>Welcome back</CardTitle>
          <CardDescription>Sign in to your account to continue.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="identifier">Matricule or email</Label>
              <Input
                id="identifier"
                autoComplete="username"
                placeholder="191234 or you@univ.dz"
                disabled={isSubmitting}
                {...register('identifier', { required: true })}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="pr-9"
                  disabled={isSubmitting}
                  {...register('password', { required: true })}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  className="absolute inset-y-0 right-0 flex items-center px-2.5 text-muted-foreground transition-colors hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </div>

            {serverError && (
              <p
                role="alert"
                className="rounded-lg border border-status-error-border bg-status-error-bg px-3 py-2 text-sm text-status-error-fg"
              >
                {serverError}
              </p>
            )}

            <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <p className="text-center text-sm text-muted-foreground">
        <Link
          href="/forgot-password"
          className="text-primary underline-offset-4 hover:underline"
        >
          Forgot your password?
        </Link>
      </p>
    </div>
  )
}

import type { Metadata } from 'next'
import { Suspense } from 'react'
import { LoginView } from './login-view'

export const metadata: Metadata = { title: 'Sign In — GradeX · ESI-SBA' }

export default function LoginPage() {
  // Suspense is required because LoginView calls useSearchParams()
  return (
    <Suspense>
      <LoginView />
    </Suspense>
  )
}

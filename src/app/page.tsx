'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'

export default function RootPage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (isLoading) return
    if (!user) { router.replace('/login'); return }

    if (user.platform_access_level) { router.replace('/admin'); return }
    switch (user.business_identity) {
      case 'STUDENT': router.replace('/student'); break
      case 'TEACHER': router.replace('/teacher'); break
      case 'EXTERNAL_SUPERVISOR': router.replace('/teacher'); break
      default: router.replace('/login')
    }
  }, [user, isLoading, router])

  return null
}

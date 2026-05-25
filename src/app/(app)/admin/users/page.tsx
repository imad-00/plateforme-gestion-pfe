import type { Metadata } from 'next'
import { Suspense } from 'react'
import { UsersView } from './users-view'

export const metadata: Metadata = { title: 'Users — GradeX' }

export default function AdminUsersPage() {
  return (
    <Suspense>
      <UsersView />
    </Suspense>
  )
}

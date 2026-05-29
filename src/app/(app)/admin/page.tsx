import type { Metadata } from 'next'
import { Suspense } from 'react'
import { AdminDashboardView } from './admin-dashboard-view'

export const metadata: Metadata = { title: 'Dashboard — GradeX' }

export default function AdminDashboardPage() {
  return (
    <Suspense>
      <AdminDashboardView />
    </Suspense>
  )
}

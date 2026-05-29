import type { Metadata } from 'next'
import { Suspense } from 'react'
import { StudentDashboardView } from './student-dashboard-view'

export const metadata: Metadata = { title: 'Dashboard — GradeX' }

export default function StudentDashboardPage() {
  return (
    <Suspense>
      <StudentDashboardView />
    </Suspense>
  )
}

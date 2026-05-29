import type { Metadata } from 'next'
import { Suspense } from 'react'
import { TeacherDashboardView } from './teacher-dashboard-view'

export const metadata: Metadata = { title: 'Dashboard — GradeX' }

export default function TeacherDashboardPage() {
  return (
    <Suspense>
      <TeacherDashboardView />
    </Suspense>
  )
}

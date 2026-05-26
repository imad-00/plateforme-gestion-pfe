import type { Metadata } from 'next'
import { Suspense } from 'react'
import { AdminAssignmentsView } from './assignments-view'

export const metadata: Metadata = { title: 'Assignments — GradeX' }

export default function AssignmentsPage() {
  return (
    <Suspense>
      <AdminAssignmentsView />
    </Suspense>
  )
}

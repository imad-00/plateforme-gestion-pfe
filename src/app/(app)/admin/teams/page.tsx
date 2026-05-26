import type { Metadata } from 'next'
import { Suspense } from 'react'
import { AdminTeamsView } from './teams-view'

export const metadata: Metadata = { title: 'Teams — GradeX' }

export default function AdminTeamsPage() {
  return (
    <Suspense>
      <AdminTeamsView />
    </Suspense>
  )
}

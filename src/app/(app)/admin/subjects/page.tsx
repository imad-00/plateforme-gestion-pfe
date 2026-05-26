import type { Metadata } from 'next'
import { Suspense } from 'react'
import { AdminSubjectsView } from './subjects-view'

export const metadata: Metadata = { title: 'Subject Moderation — GradeX' }

export default function AdminSubjectsPage() {
  return (
    <Suspense>
      <AdminSubjectsView />
    </Suspense>
  )
}

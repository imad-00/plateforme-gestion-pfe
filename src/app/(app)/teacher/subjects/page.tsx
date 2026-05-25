import type { Metadata } from 'next'
import { Suspense } from 'react'
import { TeacherSubjectsView } from './subjects-view'

export const metadata: Metadata = { title: 'My Subjects — GradeX' }

export default function TeacherSubjectsPage() {
  return (
    <Suspense>
      <TeacherSubjectsView />
    </Suspense>
  )
}

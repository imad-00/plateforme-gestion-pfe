import type { Metadata } from 'next'
import { Suspense } from 'react'
import { SubjectsView } from './subjects-view'

export const metadata: Metadata = { title: 'Subjects — GradeX' }

export default function StudentSubjectsPage() {
  return (
    <Suspense>
      <SubjectsView />
    </Suspense>
  )
}

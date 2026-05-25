import type { Metadata } from 'next'
import { Suspense } from 'react'
import { AcademicYearsView } from './academic-years-view'

export const metadata: Metadata = { title: 'Academic Years — GradeX' }

export default function AcademicYearsPage() {
  return (
    <Suspense>
      <AcademicYearsView />
    </Suspense>
  )
}

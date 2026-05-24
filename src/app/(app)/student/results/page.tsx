import type { Metadata } from 'next'
import { Suspense } from 'react'
import { ResultsView } from './results-view'

export const metadata: Metadata = { title: 'Results — GradeX' }

export default function ResultsPage() {
  return (
    <Suspense>
      <ResultsView />
    </Suspense>
  )
}

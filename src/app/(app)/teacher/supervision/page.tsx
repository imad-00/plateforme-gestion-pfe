import type { Metadata } from 'next'
import { Suspense } from 'react'
import { SupervisionView } from './supervision-view'

export const metadata: Metadata = { title: 'Supervision — GradeX' }

export default function SupervisionPage() {
  return (
    <Suspense>
      <SupervisionView />
    </Suspense>
  )
}

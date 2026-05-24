import type { Metadata } from 'next'
import { Suspense } from 'react'
import { DeliverablesView } from './deliverables-view'

export const metadata: Metadata = { title: 'Deliverables — GradeX' }

export default function DeliverablesPage() {
  return (
    <Suspense>
      <DeliverablesView />
    </Suspense>
  )
}

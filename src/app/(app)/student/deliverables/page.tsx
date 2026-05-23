import type { Metadata } from 'next'
import { PageHeader } from '@/components/layout/page-header'

export const metadata: Metadata = { title: 'Deliverables — GradeX' }

export default function DeliverablesPage() {
  return (
    <>
      <PageHeader title="Deliverables" description="Upload and track your project deliverable files." />
      <p className="text-sm text-muted-foreground">Coming soon.</p>
    </>
  )
}

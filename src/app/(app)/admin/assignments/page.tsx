import type { Metadata } from 'next'
import { PageHeader } from '@/components/layout/page-header'

export const metadata: Metadata = { title: 'Assignments — GradeX' }

export default function AssignmentsPage() {
  return (
    <>
      <PageHeader title="Assignments" description="Run assignment algorithms and review appeals." />
      <p className="text-sm text-muted-foreground">Coming soon.</p>
    </>
  )
}

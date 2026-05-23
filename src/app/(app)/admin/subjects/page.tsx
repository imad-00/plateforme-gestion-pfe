import type { Metadata } from 'next'
import { PageHeader } from '@/components/layout/page-header'

export const metadata: Metadata = { title: 'Subjects — GradeX' }

export default function AdminSubjectsPage() {
  return (
    <>
      <PageHeader title="Subjects" description="Review and moderate subject proposals." />
      <p className="text-sm text-muted-foreground">Coming soon.</p>
    </>
  )
}

import type { Metadata } from 'next'
import { PageHeader } from '@/components/layout/page-header'

export const metadata: Metadata = { title: 'Teams — GradeX' }

export default function AdminTeamsPage() {
  return (
    <>
      <PageHeader title="Teams" description="Manage teams, supervisors, and memberships." />
      <p className="text-sm text-muted-foreground">Coming soon.</p>
    </>
  )
}

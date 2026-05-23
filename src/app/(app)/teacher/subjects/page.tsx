import type { Metadata } from 'next'
import { PageHeader } from '@/components/layout/page-header'

export const metadata: Metadata = { title: 'My Subjects — GradeX' }

export default function TeacherSubjectsPage() {
  return (
    <>
      <PageHeader title="My Subjects" description="Propose and manage your PFE subjects." />
      <p className="text-sm text-muted-foreground">Coming soon.</p>
    </>
  )
}

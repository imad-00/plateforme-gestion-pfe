import type { Metadata } from 'next'
import { PageHeader } from '@/components/layout/page-header'

export const metadata: Metadata = { title: 'Supervision — GradeX' }

export default function SupervisionPage() {
  return (
    <>
      <PageHeader title="Supervision" description="Review deliverables and manage your supervised teams." />
      <p className="text-sm text-muted-foreground">Coming soon.</p>
    </>
  )
}

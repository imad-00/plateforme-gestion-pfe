import type { Metadata } from 'next'
import { PageHeader } from '@/components/layout/page-header'

export const metadata: Metadata = { title: 'My Team — GradeX' }

export default function TeamPage() {
  return (
    <>
      <PageHeader title="My Team" description="View and manage your project team." />
      <p className="text-sm text-muted-foreground">Coming soon.</p>
    </>
  )
}

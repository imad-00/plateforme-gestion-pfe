import type { Metadata } from 'next'
import { PageHeader } from '@/components/layout/page-header'

export const metadata: Metadata = { title: 'Subjects — GradeX' }

export default function StudentSubjectsPage() {
  return (
    <>
      <PageHeader title="Subjects" description="Browse the subject catalog and submit your wishlist." />
      <p className="text-sm text-muted-foreground">Coming soon.</p>
    </>
  )
}

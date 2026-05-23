import type { Metadata } from 'next'
import { PageHeader } from '@/components/layout/page-header'

export const metadata: Metadata = { title: 'Results — GradeX' }

export default function ResultsPage() {
  return (
    <>
      <PageHeader title="Results" description="View your assignment result and submit an appeal." />
      <p className="text-sm text-muted-foreground">Coming soon.</p>
    </>
  )
}

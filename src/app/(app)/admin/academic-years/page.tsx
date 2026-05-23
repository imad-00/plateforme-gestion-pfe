import type { Metadata } from 'next'
import { PageHeader } from '@/components/layout/page-header'

export const metadata: Metadata = { title: 'Academic Years — GradeX' }

export default function AcademicYearsPage() {
  return (
    <>
      <PageHeader title="Academic Years" description="Manage academic years and campaign phases." />
      <p className="text-sm text-muted-foreground">Coming soon.</p>
    </>
  )
}

import type { Metadata } from 'next'
import { PageHeader } from '@/components/layout/page-header'

export const metadata: Metadata = { title: 'Users — GradeX' }

export default function AdminUsersPage() {
  return (
    <>
      <PageHeader title="Users" description="Manage platform users and access grants." />
      <p className="text-sm text-muted-foreground">Coming soon.</p>
    </>
  )
}

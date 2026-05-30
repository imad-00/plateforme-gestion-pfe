import type { Metadata } from 'next'
import { AuditView } from './audit-view'

export const metadata: Metadata = { title: 'Audit log — GradeX Admin' }

export default function AdminAuditPage() {
  return <AuditView />
}

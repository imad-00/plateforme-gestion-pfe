import type { Metadata } from 'next'
import { ReportsView } from './reports-view'

export const metadata: Metadata = { title: 'Reports — GradeX Admin' }

export default function AdminReportsPage() {
  return <ReportsView />
}

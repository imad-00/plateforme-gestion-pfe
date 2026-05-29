import type { Metadata } from 'next'
import { AdminDefensesView } from './defenses-view'

export const metadata: Metadata = { title: 'Defenses — GradeX Admin' }

export default function AdminDefensesPage() {
  return <AdminDefensesView />
}

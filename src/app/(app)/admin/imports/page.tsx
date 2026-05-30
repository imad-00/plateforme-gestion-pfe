import type { Metadata } from 'next'
import { ImportsView } from './imports-view'

export const metadata: Metadata = { title: 'Imports — GradeX Admin' }

export default function AdminImportsPage() {
  return <ImportsView />
}

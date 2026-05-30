import type { Metadata } from 'next'
import { HistoryView } from './history-view'

export const metadata: Metadata = { title: 'History — GradeX Admin' }

export default function AdminHistoryPage() {
  return <HistoryView />
}
